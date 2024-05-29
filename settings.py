import yaml

def load_config(config_file='config.yaml'):
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

SERVER_URL = config['SERVER_URL']
TARGET_FOLDER = config['TARGET_FOLDER']
FILELIST_URL = config['FILELIST_URL']
DOWNLOAD_SPEED_LIMIT = config['DOWNLOAD_SPEED_LIMIT']
MULTITHREADING_THRESHOLD = config['MULTITHREADING_THRESHOLD']
PROGRESS_FILE_MAX_AGE = config.get('PROGRESS_FILE_MAX_AGE', 86400)