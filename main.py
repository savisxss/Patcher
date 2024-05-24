from gui import run
from utils import handle_shutdown_signals
from logger import log_info

if __name__ == '__main__':
    log_info("Patcher application starting...")
    handle_shutdown_signals()
    run()