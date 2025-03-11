import sys
import os
from gui import run
from utils import handle_shutdown_signals
from logger import log_info, log_error
from settings import SERVER_URL, TARGET_FOLDER, FILELIST_URL

def check_environment():
    """Check the environment and print basic info."""
    log_info("Patcher application starting...")
    log_info(f"Python version: {sys.version}")
    log_info(f"Running from: {os.path.abspath('.')}")
    log_info(f"Server URL: {SERVER_URL}")
    log_info(f"Target folder: {TARGET_FOLDER}")
    log_info(f"File list URL: {FILELIST_URL}")
    
    # Check for missing dependencies
    try:
        import aiohttp
        import aiofiles
        import yaml
        from PyQt5.QtWidgets import QApplication
    except ImportError as e:
        log_error(f"Missing dependency: {e}")
        print(f"Error: Missing dependency: {e}")
        print("Please install the required dependencies with: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == '__main__':
    check_environment()
    handle_shutdown_signals()
    run()