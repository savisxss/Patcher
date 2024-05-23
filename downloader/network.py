import requests
import time
import os
from settings import DOWNLOAD_SPEED_LIMIT
from logger import log_info, log_error, log_debug
from concurrent.futures import ThreadPoolExecutor
from downloader.file_manager import get_file_hash

def download_file(file_url, destination, expected_checksum, callback=None, retry_count=3, timeout=10, num_threads=4):
    def download_file_segment(url, start_byte, end_byte, part_num, destination):
        headers = {'Range': f'bytes={start_byte}-{end_byte}'}
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        part_file_name = f"{destination}.part{part_num}"
        with open(part_file_name, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        return part_file_name

    def combine_file_parts(destination, num_parts):
        with open(destination, 'wb') as final_file:
            for part_num in range(num_parts):
                part_file_name = f"{destination}.part{part_num}"
                with open(part_file_name, 'rb', buffering=0) as part_file:
                    while chunk := part_file.read(8192):
                        final_file.write(chunk)
                os.remove(part_file_name)

    max_backoff_time = 120
    backoff_factor = 2
    backoff_time = 1

    if DOWNLOAD_SPEED_LIMIT > 0:
        throttle_interval = (8192 / (DOWNLOAD_SPEED_LIMIT * 1024))
    else:
        throttle_interval = 0

    for attempt in range(retry_count):
        try:
            response = requests.head(file_url, timeout=timeout, headers={'Accept-Encoding': 'gzip, deflate'})
            response.raise_for_status()
            total_size_in_bytes = int(response.headers.get('content-length', 0))
            part_size = total_size_in_bytes // num_threads
            futures = []

            log_debug(f'Starting download: {file_url}')

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                for part_num in range(num_threads):
                    start_byte = part_num * part_size
                    end_byte = start_byte + part_size - 1 if part_num < num_threads - 1 else total_size_in_bytes - 1
                    futures.append(executor.submit(download_file_segment, file_url, start_byte, end_byte, part_num, destination))

                downloaded_size = 0
                for future in futures:
                    future.result()
                    downloaded_size += part_size
                    if callback:
                        callback(downloaded_size, total_size_in_bytes)
                    if throttle_interval > 0:
                        time.sleep(throttle_interval)

            combine_file_parts(destination, num_threads)
            actual_checksum = get_file_hash(destination)
            if actual_checksum != expected_checksum:
                log_error(f'Checksum mismatch: expected {expected_checksum}, got {actual_checksum}')
                raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")

            log_info(f'File downloaded and checksum verified: {destination}')
            return
        except requests.exceptions.HTTPError as e:
            log_error(f'HTTP error: {e}')
        except requests.exceptions.ConnectionError as e:
            log_error(f'Connection error: {e}')
        except requests.exceptions.Timeout as e:
            log_error(f'Timeout error: {e}')
        except requests.exceptions.RequestException as e:
            log_error(f'Error downloading file {file_url}: {e}')
        except ValueError as e:
            log_error(f'Checksum error: {e}')

        if attempt < retry_count - 1:
            backoff_time = min(backoff_time * backoff_factor, max_backoff_time)
            log_info(f'Retrying to download file: {file_url}, Attempt: {attempt + 2}, Waiting for {backoff_time} seconds')
            time.sleep(backoff_time)
        else:
            log_error(f'Failed to download file after {retry_count} attempts: {file_url}')
            if callback:
                callback(None, None, error='Failed to download file after maximum retry attempts')
            raise Exception(f"Failed to download file after {retry_count} attempts: {file_url}")