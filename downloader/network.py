import requests
import time
from settings import DOWNLOAD_SPEED_LIMIT
from logger import log_info, log_error, log_debug

def download_file(file_url, destination, callback=None, retry_count=3, timeout=10):
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