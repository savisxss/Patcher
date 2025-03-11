import os
import aiohttp
import asyncio
from settings import SERVER_URL, TARGET_FOLDER, FILELIST_URL, MULTITHREADING_THRESHOLD, PROGRESS_FILE_MAX_AGE
from .file_manager import create_directory_if_not_exists, get_file_hash, clean_old_progress_files
from .network import resume_download
from logger import log_info, log_error, log_debug

async def is_file_update_needed(file_name, server_file_hash):
    """Check if a file needs to be updated based on hash comparison."""
    local_file_path = os.path.join(TARGET_FOLDER, file_name)
    
    # If file doesn't exist, it needs an update
    if not os.path.exists(local_file_path):
        return True
    
    try:
        # Compare file hashes
        local_file_hash = await get_file_hash(local_file_path)
        return local_file_hash != server_file_hash
    except Exception as e:
        log_error(f"Error checking file {file_name}: {e}")
        # If we can't check the file, assume it needs an update
        return True

async def update_files(callback=None):
    """Update files based on the server file list."""
    status_report = {
        'updated': [], 
        'skipped': [], 
        'failed': [], 
        'verification': {'verified': [], 'corrupted': []}
    }
    
    files_to_verify = {}
    connection_error = False
    
    try:
        # Ensure target directory exists
        await create_directory_if_not_exists(TARGET_FOLDER)
        
        # Create an optimized session with proper timeout and connection pooling
        conn = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            try:
                # Fetch the file list
                async with session.get(FILELIST_URL) as response:
                    response.raise_for_status()
                    filelist_text = await response.text()
                    
                # Parse the file list
                filelist = [line.strip() for line in filelist_text.split('\n') if line.strip()]
                
                # Process each file
                total_files = len(filelist)
                log_info(f"Found {total_files} files to process")
                
                # Create a semaphore to limit concurrent downloads
                semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent downloads
                
                async def process_file(file_entry, file_index):
                    try:
                        if ',' not in file_entry:
                            log_error(f'Invalid file entry format: {file_entry}')
                            status_report['failed'].append(file_entry)
                            return
                        
                        file_name, server_file_hash = file_entry.split(',')
                        file_path = os.path.join(TARGET_FOLDER, file_name)
                        file_url = f'{SERVER_URL}{file_name}'
                        
                        # Ensure directory exists for the file
                        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                        
                        # Check if update is needed
                        update_needed = await is_file_update_needed(file_name, server_file_hash)
                        
                        if update_needed:
                            # Get file size to determine download strategy
                            try:
                                async with session.head(file_url) as head_response:
                                    head_response.raise_for_status()
                                    file_size = int(head_response.headers.get('Content-Length', 0))
                            except Exception as e:
                                log_error(f"Error getting size for {file_name}: {e}")
                                file_size = MULTITHREADING_THRESHOLD + 1  # Default to multi-threading
                            
                            log_info(f'Updating file: {file_name} ({file_size} bytes)')
                            
                            # Determine thread count based on file size
                            if file_size > MULTITHREADING_THRESHOLD:
                                thread_count = min(8, max(2, file_size // (5 * 1024 * 1024)))  # 1 thread per 5MB, max 8
                                log_debug(f'Using {thread_count} threads for {file_name}')
                                
                                async with semaphore:
                                    await resume_download(
                                        file_url, file_path, server_file_hash,
                                        num_threads=thread_count, 
                                        callback=lambda p, t, **kwargs: callback(file_index + (p/t if t else 0), total_files, **kwargs) if callback else None
                                    )
                            else:
                                log_debug(f'Using single thread for {file_name}')
                                
                                async with semaphore:
                                    await resume_download(
                                        file_url, file_path, server_file_hash,
                                        num_threads=1,
                                        callback=lambda p, t, **kwargs: callback(file_index + (p/t if t else 0), total_files, **kwargs) if callback else None
                                    )
                            
                            log_info(f'File updated: {file_name}')
                            status_report['updated'].append(file_name)
                            files_to_verify[file_name] = server_file_hash
                        else:
                            log_info(f'File is up-to-date: {file_name}')
                            status_report['skipped'].append(file_name)
                        
                        # Report progress
                        if callback:
                            callback(file_index + 1, total_files)
                            
                    except aiohttp.ClientError as e:
                        log_error(f'Network error for {file_entry}: {e}')
                        status_report['failed'].append(file_entry.split(',')[0] if ',' in file_entry else file_entry)
                    except Exception as e:
                        log_error(f'Error processing {file_entry}: {e}')
                        status_report['failed'].append(file_entry.split(',')[0] if ',' in file_entry else file_entry)
                
                # Create tasks for all files
                tasks = [process_file(file_entry, i) for i, file_entry in enumerate(filelist)]
                await asyncio.gather(*tasks)
                
                # Verify file integrity
                verification_report = await verify_file_integrity(files_to_verify, callback)
                status_report['verification'] = verification_report
                
                # Clean up old progress files
                await clean_old_progress_files(TARGET_FOLDER, PROGRESS_FILE_MAX_AGE)
                
            except aiohttp.ClientError as e:
                log_error(f'Error fetching file list: {e}')
                connection_error = True
                
    except Exception as e:
        log_error(f'Unexpected error in update process: {e}')
    
    if connection_error and callback:
        callback(None, None, error="Connection error: Could not fetch file list")
    
    return status_report

async def verify_file_integrity(files_to_verify, callback=None):
    """Verify the integrity of downloaded files."""
    verification_report = {'verified': [], 'corrupted': []}
    
    # Skip if no files to verify
    if not files_to_verify:
        return verification_report
    
    total_files = len(files_to_verify)
    log_info(f'Verifying integrity of {total_files} files')
    
    # Create tasks for parallel verification
    async def verify_file(file_name, expected_checksum, index):
        local_file_path = os.path.join(TARGET_FOLDER, file_name)
        
        if not os.path.exists(local_file_path):
            log_error(f'File missing for verification: {file_name}')
            verification_report['corrupted'].append(file_name)
            return
        
        try:
            local_file_hash = await get_file_hash(local_file_path)
            
            if local_file_hash == expected_checksum:
                log_info(f'File integrity verified: {file_name}')
                verification_report['verified'].append(file_name)
            else:
                log_error(f'File integrity check failed: {file_name}')
                verification_report['corrupted'].append(file_name)
        except Exception as e:
            log_error(f'Error verifying file {file_name}: {e}')
            verification_report['corrupted'].append(file_name)
        
        # Report progress
        if callback:
            callback(index + 1, total_files)
    
    # Create and run verification tasks
    tasks = [
        verify_file(file_name, expected_checksum, i)
        for i, (file_name, expected_checksum) in enumerate(files_to_verify.items())
    ]
    await asyncio.gather(*tasks)
    
    return verification_report