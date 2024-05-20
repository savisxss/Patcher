import os
import requests
from settings import SERVER_URL, TARGET_FOLDER, FILELIST_URL, MULTITHREADING_THRESHOLD
from .file_manager import create_directory_if_not_exists, get_file_hash
from .network import download_file, download_file_multithreaded
from logger import log_info, log_error, log_debug

def is_file_update_needed(file_name, server_file_hash):
    local_file_path = os.path.join(TARGET_FOLDER, file_name)
    if not os.path.exists(local_file_path):
        return True
    local_file_hash = get_file_hash(local_file_path)
    return local_file_hash != server_file_hash

def update_files(callback=None, use_multithreading=False):
    status_report = {'updated': [], 'skipped': [], 'failed': []}
    try:
        create_directory_if_not_exists(TARGET_FOLDER)
        filelist_response = requests.get(FILELIST_URL)
        filelist_response.raise_for_status()
        filelist = filelist_response.text.strip().split('\n')

        total_files = len(filelist)
        updated_files = 0

        for file_entry in filelist:
            if ',' in file_entry:
                file_name, server_file_hash = file_entry.split(',')
                log_debug(f'Processing file: {file_name}')
                file_url = f'{SERVER_URL}{file_name}'

                if is_file_update_needed(file_name, server_file_hash):
                    try:
                        head_response = requests.head(file_url)
                        file_size = int(head_response.headers.get('Content-Length', 0))

                        if file_size > MULTITHREADING_THRESHOLD:
                            log_info(f'Using multithreaded download for {file_name}')
                            download_file_multithreaded(file_url, os.path.join(TARGET_FOLDER, file_name))
                        else:
                            log_info(f'Using single-threaded download for {file_name}')
                            download_file(file_url, os.path.join(TARGET_FOLDER, file_name), callback=callback)

                        log_info(f'File updated: {file_name}')
                        status_report['updated'].append(file_name)
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
    except requests.exceptions.RequestException as e:
        log_error(f'Error fetching file list: {e}')

    return status_report