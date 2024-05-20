import requests
import time
import os
from settings import DOWNLOAD_SPEED_LIMIT
from logger import log_info, log_error, log_debug
from concurrent.futures import ThreadPoolExecutor

def download_file(file_url, destination, callback=None, retry_count=3, timeout=10, multithreaded=False):
    if multithreaded:
        download_file_multithreaded(file_url, destination)
    else:
        if DOWNLOAD_SPEED_LIMIT > 0:
            throttle_interval = (8192 / (DOWNLOAD_SPEED_LIMIT * 1024))
        else:
            throttle_interval = 0

        for attempt in range(retry_count):
            try:
                response = requests.get(file_url, stream=True, timeout=timeout, headers={'Accept-Encoding': 'gzip, deflate'})
                response.raise_for_status()
                total_size_in_bytes = int(response.headers.get('content-length', 0))
                block_size = 8192
                downloaded_size = 0
                log_debug(f'Starting download: {file_url}')

                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if callback:
                                callback(downloaded_size, total_size_in_bytes)
                            if throttle_interval > 0:
                                time.sleep(throttle_interval)
                log_info(f'File downloaded: {destination}')
                return
            except requests.exceptions.HTTPError as e:
                log_error(f'HTTP error: {e}')
            except requests.exceptions.ConnectionError as e:
                log_error(f'Connection error: {e}')
            except requests.exceptions.Timeout as e:
                log_error(f'Timeout error: {e}')
            except requests.exceptions.RequestException as e:
                log_error(f'Error downloading file {file_url}: {e}')

            if callback:
                callback(None, None, error=f'Attempt {attempt + 1} failed')
            log_info(f'Retrying to download file: {file_url}, Attempt: {attempt + 1}')

        raise Exception(f"Failed to download file after {retry_count} attempts: {file_url}")

def download_file_segment(url, start_byte, end_byte, part_num, destination):
    headers = {'Range': f'bytes={start_byte}-{end_byte}'}
    response = requests.get(url, headers=headers, stream=True)
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
            with open(part_file_name, 'rb') as part_file:
                final_file.write(part_file.read())
            os.remove(part_file_name)

def download_file_multithreaded(file_url, destination, num_threads=4):
    response = requests.head(file_url)
    file_size = int(response.headers.get('content-length', 0))
    part_size = file_size // num_threads
    futures = []

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        for part_num in range(num_threads):
            start_byte = part_num * part_size
            end_byte = start_byte + part_size - 1 if part_num < num_threads - 1 else ''
            futures.append(executor.submit(download_file_segment, file_url, start_byte, end_byte, part_num, destination))

    for future in futures:
        future.result()

    combine_file_parts(destination, num_threads)
    log_info(f"File downloaded with multithreading: {destination}")