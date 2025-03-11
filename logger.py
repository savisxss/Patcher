import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure rotating file handler to prevent log files from growing too large
handler = RotatingFileHandler(
    'logs/patcher.log', 
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3
)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Configure logger
logger = logging.getLogger('patcher')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# Add a performance flag that can be toggled to reduce logging overhead in production
PERFORMANCE_MODE = False

def log_debug(message):
    if not PERFORMANCE_MODE:
        logger.debug(message)

def log_info(message):
    logger.info(message)

def log_error(message):
    logger.error(message)