import os
import aiohttp
from settings import SERVER_URL, TARGET_FOLDER, FILELIST_URL, MULTITHREADING_THRESHOLD
from .file_manager import create_directory_if_not_exists, get_file_hash
from .network import download_file
from logger import log_info, log_error, log_debug

async def is_file_update_needed(file_name, server_file_hash):
    local_file_path = os.path.join(TARGET_FOLDER, file_name)
    if not os.path.exists(local_file_path):
        return True
    local_file_hash = get_file_hash(local_file_path)
    return local_file_hash != server_file_hash

async def update_files(callback=None):
    status_report = {'updated': [], 'skipped': [], 'failed': [], 'verification': {'verified': [], 'corrupted': []}}
    files_to_verify = {}
    try:
        create_directory_if_not_exists(TARGET_FOLDER)
        async with aiohttp.ClientSession() as session:
            async with session.get(FILELIST_URL) as filelist_response:
                filelist_response.raise_for_status()
                filelist = filelist_response.text.strip().split('\n')

        total_files = len(filelist)
        updated_files = 0

        for file_entry in filelist:
            if ',' in file_entry:
                file_name, server_file_hash = file_entry.split(',')
                log_debug(f'Processing file: {file_name}')
                file_url = f'{SERVER_URL}{file_name}'

                if await is_file_update_needed(file_name, server_file_hash):
                    try:
                        async with session.head(file_url) as head_response:
                            file_size = int(head_response.headers.get('Content-Length', 0))

                        if file_size > MULTITHREADING_THRESHOLD:
                            log_info(f'Using multithreaded download for {file_name}')
                            await download_file(file_url, os.path.join(TARGET_FOLDER, file_name), server_file_hash, num_threads=4)
                        else:
                            log_info(f'Using single-threaded download for {file_name}')
                            await download_file(file_url, os.path.join(TARGET_FOLDER, file_name), server_file_hash)

                        log_info(f'File updated: {file_name}')
                        status_report['updated'].append(file_name)
                        files_to_verify[file_name] = server_file_hash
                    except Exception as e:
                        log_error(f'Error updating file {file_name}: {e}')
                        status_report['failed'].append(file_name)
                else:
                    log_info(f'File is up-to-date, skipping: {file_name}')
                    status_report['skipped'].append(file_name)
                updated_files += 1
                if callback:
                    callback(updated_files, total_files)
            else:
                log_error(f'Invalid file entry format: {file_entry}')
                status_report['failed'].append(file_entry)

        verification_report = await verify_file_integrity(files_to_verify)
        status_report['verification'] = verification_report
    except aiohttp.ClientError as e:
        log_error(f'Error fetching file list: {e}')

    return status_report

async def verify_file_integrity(files_to_verify):
    verification_report = {'verified': [], 'corrupted': []}
    for file_name, expected_checksum in files_to_verify.items():
        local_file_path = os.path.join(TARGET_FOLDER, file_name)
        if os.path.exists(local_file_path):
            local_file_hash = get_file_hash(local_file_path)
            if local_file_hash == expected_checksum:
                log_info(f'File integrity verified for {file_name}')
                verification_report['verified'].append(file_name)
            else:
                log_error(f'File integrity check failed for {file_name}')
                verification_report['corrupted'].append(file_name)
    return verification_report