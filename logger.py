import logging

logging.basicConfig(filename='patcher.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def log_debug(message):
    logging.debug(message)

def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)