import sys
import signal
from logger import log_info

def handle_shutdown_signals():
    def signal_handler(sig, frame):
        log_info(f"Received signal {sig}. Shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)