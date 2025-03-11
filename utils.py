import sys
import signal
import os
import platform
import psutil
import time
from logger import log_info, log_error, log_debug

def handle_shutdown_signals():
    """Setup handlers for clean shutdown on termination signals."""
    def signal_handler(sig, frame):
        log_info(f"Received signal {sig}. Shutting down gracefully...")
        # Clean up any temporary files
        cleanup_temp_files()
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows doesn't support SIGUSR1
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, signal_handler)

def cleanup_temp_files(directory='.'):
    """Clean up temporary part files from interrupted downloads."""
    try:
        for file in os.listdir(directory):
            if file.endswith('.part0') or file.endswith('.progress'):
                try:
                    os.remove(os.path.join(directory, file))
                    log_debug(f"Removed temporary file: {file}")
                except OSError as e:
                    log_error(f"Failed to remove temporary file {file}: {e}")
    except Exception as e:
        log_error(f"Error during temp file cleanup: {e}")

def check_disk_space(directory, min_space_mb=100):
    """Check if there's enough disk space available."""
    try:
        free_space = psutil.disk_usage(directory).free / (1024 * 1024)  # Convert to MB
        log_debug(f"Free disk space: {free_space:.2f} MB")
        
        if free_space < min_space_mb:
            log_error(f"Low disk space warning: {free_space:.2f} MB available, minimum {min_space_mb} MB recommended")
            return False, free_space
        return True, free_space
    except Exception as e:
        log_error(f"Error checking disk space: {e}")
        return False, 0

def format_size(size_bytes):
    """Format file size in a human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

def format_time(seconds):
    """Format time duration in a human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def measure_performance(func):
    """Decorator to measure execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        log_debug(f"Function {func.__name__} took {duration:.3f} seconds to execute")
        return result
    return wrapper

def is_valid_url(url):
    """Check if a URL is properly formatted."""
    import re
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None