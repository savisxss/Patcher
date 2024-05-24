import os
import hashlib
from logger import log_info, log_error

def create_directory_if_not_exists(directory_path):
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
            log_info(f'Directory created: {directory_path}')
    except OSError as e:
        log_error(f"Error creating directory {directory_path}: {e}")
        raise Exception(f"Error creating directory {directory_path}: {e}")

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, 'rb', buffering=0) as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except OSError as e:
        log_error(f"Error reading file {file_path}: {e}")
        raise Exception(f"Error reading file {file_path}: {e}")

def save_progress(file_path, progress):
    try:
        with open(f"{file_path}.progress", 'w') as f:
            f.write(str(progress))
    except OSError as e:
        log_error(f"Error saving progress for {file_path}: {e}")

def load_progress(file_path):
    try:
        with open(f"{file_path}.progress", 'r') as f:
            return int(f.read())
    except (OSError, ValueError):
        return 0

def remove_progress_file(file_path):
    try:
        os.remove(f"{file_path}.progress")
    except OSError as e:
        log_error(f"Error removing progress file for {file_path}: {e}")