import aiohttp
import asyncio
import os
from settings import DOWNLOAD_SPEED_LIMIT
from logger import log_info, log_error, log_debug
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from downloader.file_manager import get_file_hash, save_progress, load_progress, remove_progress_file

# Optimized chunk sizes for different operations
DOWNLOAD_CHUNK_SIZE = 262144  # 256KB
COMBINE_CHUNK_SIZE = 1048576  # 1MB

async def download_file_segment(session, url, start_byte, end_byte, part_num, destination, throttle_interval=0):
    """Download a segment of a file."""
    headers = {'Range': f'bytes={start_byte}-{end_byte}'}
    part_file_name = f"{destination}.part{part_num}"
    
    try:
        # Ensure any existing part file is removed
        if os.path.exists(part_file_name):
            os.remove(part_file_name)

        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            
            # Preallocate the file to avoid fragmentation
            total_size = end_byte - start_byte + 1
            
            async with aiofiles.open(part_file_name, 'wb') as file:
                bytes_downloaded = 0
                async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                    await file.write(chunk)
                    bytes_downloaded += len(chunk)
                    
                    # Apply throttling if needed
                    if throttle_interval > 0:
                        await asyncio.sleep(throttle_interval)
        
        return part_file_name, bytes_downloaded
    except Exception as e:
        log_error(f"Error downloading segment {part_num}: {e}")
        # Remove partial file if there's an error
        if os.path.exists(part_file_name):
            os.remove(part_file_name)
        raise

async def combine_file_parts(destination, num_parts):
    """Combine file parts efficiently."""
    try:
        # Ensure the destination directory exists
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        
        async with aiofiles.open(destination, 'wb') as final_file:
            for part_num in range(num_parts):
                part_file_name = f"{destination}.part{part_num}"
                if not os.path.exists(part_file_name):
                    raise FileNotFoundError(f"Part file missing: {part_file_name}")
                
                # Use a larger buffer for combining
                async with aiofiles.open(part_file_name, 'rb') as part_file:
                    while True:
                        chunk = await part_file.read(COMBINE_CHUNK_SIZE)
                        if not chunk:
                            break
                        await final_file.write(chunk)
                
                # Remove part file after combining
                os.remove(part_file_name)
                log_debug(f"Removed part file: {part_file_name}")
    except Exception as e:
        log_error(f"Error combining file parts for {destination}: {e}")
        raise

async def download_file(file_url, destination, expected_checksum, callback=None, retry_count=3, timeout=30, num_threads=4):
    """Download a file with advanced error handling and retry logic."""
    max_backoff_time = 120
    backoff_factor = 2
    backoff_time = 1
    
    # Calculate throttling interval if speed limit is set
    throttle_interval = (DOWNLOAD_CHUNK_SIZE / (DOWNLOAD_SPEED_LIMIT * 1024)) if DOWNLOAD_SPEED_LIMIT > 0 else 0
    
    # Ensure the destination directory exists
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    
    for attempt in range(retry_count):
        try:
            # Create timeout context for better responsiveness
            timeout_ctx = aiohttp.ClientTimeout(total=timeout, connect=10, sock_connect=10, sock_read=10)
            
            async with aiohttp.ClientSession(timeout=timeout_ctx) as session:
                # Get file size
                async with session.head(file_url) as response:
                    response.raise_for_status()
                    total_size_in_bytes = int(response.headers.get('Content-Length', 0))
                    if total_size_in_bytes == 0:
                        raise ValueError("Failed to retrieve the total size of the file.")
                
                # Calculate optimal part size and thread count
                # For small files, reduce thread count
                if total_size_in_bytes < 1024 * 1024:  # 1MB
                    num_threads = 1
                elif total_size_in_bytes < 10 * 1024 * 1024:  # 10MB
                    num_threads = min(2, num_threads)
                
                part_size = total_size_in_bytes // num_threads
                if part_size < DOWNLOAD_CHUNK_SIZE:
                    num_threads = max(1, total_size_in_bytes // DOWNLOAD_CHUNK_SIZE)
                    part_size = total_size_in_bytes // max(1, num_threads)
                
                log_debug(f'Starting download of {file_url} with {num_threads} threads')
                
                # Prepare the download tasks
                tasks = []
                for part_num in range(num_threads):
                    start_byte = part_num * part_size
                    end_byte = (start_byte + part_size - 1) if part_num < num_threads - 1 else (total_size_in_bytes - 1)
                    tasks.append(download_file_segment(
                        session, file_url, start_byte, end_byte, part_num, 
                        destination, throttle_interval
                    ))
                
                # Execute downloads
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check for any failed segments
                failed_segments = [i for i, result in enumerate(results) if isinstance(result, Exception)]
                if failed_segments:
                    raise Exception(f"Failed to download segments: {failed_segments}")
                
                # Combine all parts
                await combine_file_parts(destination, num_threads)
                
                # Verify file
                actual_checksum = await get_file_hash(destination)
                if actual_checksum != expected_checksum:
                    raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")
                
                log_info(f'File downloaded and verified: {destination}')
                await remove_progress_file(destination)
                
                # Notify callback of completion
                if callback:
                    callback(total_size_in_bytes, total_size_in_bytes)
                
                return True
                
        except aiohttp.ClientError as e:
            log_error(f'HTTP error: {e}')
        except asyncio.TimeoutError:
            log_error(f'Timeout downloading {file_url}')
        except Exception as e:
            log_error(f'Error downloading file {file_url}: {e}')
        
        # Handle retry logic
        if attempt < retry_count - 1:
            backoff_time = min(backoff_time * backoff_factor, max_backoff_time)
            log_info(f'Retrying download: {file_url}, Attempt: {attempt + 2}, Waiting for {backoff_time} seconds')
            await asyncio.sleep(backoff_time)
        else:
            log_error(f'Failed to download after {retry_count} attempts: {file_url}')
            if callback:
                callback(None, None, error=f'Failed to download after {retry_count} attempts')
            raise Exception(f"Failed to download file after {retry_count} attempts: {file_url}")

async def resume_download(file_url, destination, expected_checksum, callback=None, retry_count=3, timeout=30, num_threads=4):
    """Resume a download if possible."""
    # First check if the file already exists and has the correct checksum
    if os.path.exists(destination):
        try:
            existing_hash = await get_file_hash(destination)
            if existing_hash == expected_checksum:
                log_info(f'File already exists with correct checksum: {destination}')
                if callback:
                    callback(1, 1)  # Report as complete
                return True
        except Exception as e:
            log_error(f'Error checking existing file: {e}')
    
    # Check for saved progress
    resume_position = await load_progress(destination)
    
    # If we have saved progress, try to resume
    if resume_position > 0:
        log_info(f'Resuming download for {destination} from byte {resume_position}')
        try:
            # Create optimized session with timeout
            timeout_ctx = aiohttp.ClientTimeout(total=timeout, connect=10, sock_connect=10, sock_read=10)
            
            async with aiohttp.ClientSession(timeout=timeout_ctx) as session:
                # Verify server supports range requests
                async with session.head(file_url) as response:
                    supports_range = 'Accept-Ranges' in response.headers and response.headers['Accept-Ranges'] == 'bytes'
                    total_size_in_bytes = int(response.headers.get('Content-Length', 0))
                    
                    if not supports_range:
                        log_info(f'Server does not support range requests, starting new download for {destination}')
                        return await download_file(file_url, destination, expected_checksum, callback, retry_count, timeout, num_threads)
                    
                    if resume_position >= total_size_in_bytes:
                        log_error(f'Invalid resume position for {destination}: {resume_position} >= {total_size_in_bytes}')
                        # Start a new download
                        return await download_file(file_url, destination, expected_checksum, callback, retry_count, timeout, num_threads)
            
            # Continue with a standard download, which will handle the resume logic
            return await download_file(file_url, destination, expected_checksum, callback, retry_count, timeout, num_threads)
            
        except Exception as e:
            log_error(f'Error resuming download: {e}')
            # Fall back to a new download
            return await download_file(file_url, destination, expected_checksum, callback, retry_count, timeout, num_threads)
    else:
        # No progress saved, start a new download
        return await download_file(file_url, destination, expected_checksum, callback, retry_count, timeout, num_threads)