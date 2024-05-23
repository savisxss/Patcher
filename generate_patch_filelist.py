import os
from downloader.file_manager import create_directory_if_not_exists, get_file_hash
from logger import log_info, log_error

TARGET_FOLDER = 'path/to/your/target/folder'
OUTPUT_FILE = 'patcher.txt'

def generate_filelist(target_folder):
    filelist = []
    for root, files in os.walk(target_folder):
        for file in files:
            filepath = os.path.join(root, file)
            file_hash = get_file_hash(filepath)
            relative_path = os.path.relpath(filepath, target_folder)
            filelist.append(f"{relative_path},{file_hash}")
    return filelist

def save_filelist(filelist, output_file):
    try:
        with open(output_file, 'w') as f:
            for file_entry in filelist:
                f.write(f"{file_entry}\n")
        log_info(f'File list has been saved to {output_file}')
    except IOError as e:
        log_error(f'Error saving file list to {output_file}: {e}')
        raise Exception(f"Error saving file list to {output_file}: {e}")

try:
    create_directory_if_not_exists(TARGET_FOLDER)
    filelist = generate_filelist(TARGET_FOLDER)
    save_filelist(filelist, OUTPUT_FILE)
except Exception as e:
    log_error(f'Error generating file list: {e}')