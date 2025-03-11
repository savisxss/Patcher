import os
import hashlib
import asyncio
import aiofiles
from logger import log_info, log_error

# Increased chunk size for better hash performance
HASH_CHUNK_SIZE = 65536  # 64KB

async def create_directory_if_not_exists(directory_path):
    """Create directory if it doesn't exist."""
    try:
        os.makedirs(directory_path, exist_ok=True)
        log_info(f'Directory ensured: {directory_path}')
    except OSError as e:
        log_error(f"Error creating directory {directory_path}: {e}")
        raise Exception(f"Error creating directory {directory_path}: {e}")

async def get_file_hash(file_path):
    """Get SHA256 hash of file with optimized chunk reading."""
    sha256_hash = hashlib.sha256()
    try:
        async with aiofiles.open(file_path, 'rb') as f:
            # Use larger chunks for better performance
            while True:
                chunk = await f.read(HASH_CHUNK_SIZE)
                if not chunk:
                    break
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except OSError as e:
        log_error(f"Error reading file {file_path}: {e}")
        raise Exception(f"Error reading file {file_path}: {e}")

async def save_progress(file_path, progress):
    """Save download progress to file."""
    try:
        progress_path = f"{file_path}.progress"
        async with aiofiles.open(progress_path, 'w') as f:
            await f.write(str(progress))
    except OSError as e:
        log_error(f"Error saving progress for {file_path}: {e}")

async def load_progress(file_path):
    """Load download progress from file."""
    try:
        progress_path = f"{file_path}.progress"
        if not os.path.exists(progress_path):
            return 0
        async with aiofiles.open(progress_path, 'r') as f:
            return int(await f.read())
    except (OSError, ValueError):
        return 0

async def remove_progress_file(file_path):
    """Remove progress file after successful download."""
    try:
        progress_path = f"{file_path}.progress"
        if os.path.exists(progress_path):
            os.remove(progress_path)
    except OSError as e:
        log_error(f"Error removing progress file for {file_path}: {e}")

async def clean_old_progress_files(directory, max_age):
    """Clean up old progress files."""
    current_time = asyncio.get_event_loop().time()
    try:
        for file_name in os.listdir(directory):
            if file_name.endswith('.progress'):
                file_path = os.path.join(directory, file_name)
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age:
                    os.remove(file_path)
                    log_info(f'Removed old progress file: {file_path}')
    except OSError as e:
        log_error(f"Error cleaning progress files: {e}")