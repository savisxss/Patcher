import aiohttp
import asyncio
import os
from settings import DOWNLOAD_SPEED_LIMIT
from logger import log_info, log_error, log_debug
from concurrent.futures import ThreadPoolExecutor
from downloader.file_manager import get_file_hash, save_progress, load_progress, remove_progress_file
import aiofiles

async def download_file_segment(session, url, start_byte, end_byte, part_num, destination):
    headers = {'Range': f'bytes={start_byte}-{end_byte}'}
    part_file_name = f"{destination}.part{part_num}"
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        async with aiofiles.open(part_file_name, 'ab') as file:
            async for chunk in response.content.iter_chunked(1024):
                await file.write(chunk)
    return part_file_name

async def combine_file_parts(destination, num_parts):
    async with aiofiles.open(destination, 'wb') as final_file:
        for part_num in range(num_parts):
            part_file_name = f"{destination}.part{part_num}"
            async with aiofiles.open(part_file_name, 'rb', buffering=0) as part_file:
                while chunk := await part_file.read(8192):
                    await final_file.write(chunk)
            os.remove(part_file_name)

async def download_file(file_url, destination, expected_checksum, callback=None, retry_count=3, timeout=10, num_threads=4):
    max_backoff_time = 120
    backoff_factor = 2
    backoff_time = 1

    throttle_interval = (8192 / (DOWNLOAD_SPEED_LIMIT * 1024)) if DOWNLOAD_SPEED_LIMIT > 0 else 0

    for attempt in range(retry_count):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.head(file_url) as response:
                    response.raise_for_status()
                    total_size_in_bytes = int(response.headers.get('Content-Length', 0))
                    if total_size_in_bytes == 0:
                        raise ValueError("Failed to retrieve the total size of the file.")

                    part_size = total_size_in_bytes // num_threads

                futures = []

                log_debug(f'Starting download: {file_url}')

                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    for part_num in range(num_threads):
                        start_byte = part_num * part_size
                        end_byte = start_byte + part_size - 1 if part_num < num_threads - 1 else total_size_in_bytes - 1
                        futures.append(loop.run_in_executor(executor, download_file_segment, session, file_url, start_byte, end_byte, part_num, destination))

                    downloaded_size = 0
                    for future in await asyncio.gather(*futures):
                        await future
                        downloaded_size += part_size
                        await save_progress(destination, downloaded_size)
                        if callback:
                            callback(downloaded_size, total_size_in_bytes)
                        if throttle_interval > 0:
                            await asyncio.sleep(throttle_interval)

                await combine_file_parts(destination, num_threads)
                actual_checksum = await get_file_hash(destination)
                if actual_checksum != expected_checksum:
                    log_error(f'Checksum mismatch: expected {expected_checksum}, got {actual_checksum}')
                    raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")

                log_info(f'File downloaded and checksum verified: {destination}')
                await remove_progress_file(destination)
                return
        except aiohttp.ClientError as e:
            log_error(f'HTTP error: {e}')
        except asyncio.TimeoutError as e:
            log_error(f'Timeout error: {e}')
        except Exception as e:
            log_error(f'Error downloading file {file_url}: {e}')

        if attempt < retry_count - 1:
            backoff_time = min(backoff_time * backoff_factor, max_backoff_time)
            log_info(f'Retrying to download file: {file_url}, Attempt: {attempt + 2}, Waiting for {backoff_time} seconds')
            await asyncio.sleep(backoff_time)
        else:
            log_error(f'Failed to download file after {retry_count} attempts: {file_url}')
            if callback:
                callback(None, None, error='Failed to download file after maximum retry attempts')
            raise Exception(f"Failed to download file after {retry_count} attempts: {file_url}")

async def resume_download(file_url, destination, expected_checksum, callback=None, retry_count=3, timeout=10, num_threads=4):
    resume_position = await load_progress(destination)
    throttle_interval = (8192 / (DOWNLOAD_SPEED_LIMIT * 1024)) if DOWNLOAD_SPEED_LIMIT > 0 else 0

    if resume_position > 0:
        log_info(f'Resuming download for {destination} from byte {resume_position}')
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.head(file_url) as response:
                response.raise_for_status()
                total_size_in_bytes = int(response.headers.get('Content-Length', 0))
                if total_size_in_bytes == 0:
                    raise ValueError("Failed to retrieve the total size of the file.")

                remaining_size = total_size_in_bytes - resume_position
                part_size = remaining_size // num_threads

                futures = []
                log_debug(f'Resuming download: {file_url}')
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    for part_num in range(num_threads):
                        start_byte = resume_position + part_num * part_size
                        end_byte = start_byte + part_size - 1 if part_num < num_threads - 1 else total_size_in_bytes - 1
                        futures.append(loop.run_in_executor(executor, download_file_segment, session, file_url, start_byte, end_byte, part_num, destination))

                    downloaded_size = resume_position
                    for future in await asyncio.gather(*futures):
                        await future
                        downloaded_size += part_size
                        await save_progress(destination, downloaded_size)
                        if callback:
                            callback(downloaded_size, total_size_in_bytes)
                        if throttle_interval > 0:
                            await asyncio.sleep(throttle_interval)

                await combine_file_parts(destination, num_threads)
                actual_checksum = await get_file_hash(destination)
                if actual_checksum != expected_checksum:
                    log_error(f'Checksum mismatch: expected {expected_checksum}, got {actual_checksum}')
                    raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")

                log_info(f'File downloaded and checksum verified: {destination}')
                await remove_progress_file(destination)
                return
    else:
        await download_file(file_url, destination, expected_checksum, callback, retry_count, timeout, num_threads)