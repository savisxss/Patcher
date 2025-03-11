import yaml
import os
from logger import log_error, log_info

def load_config(config_file='config.yaml'):
    """Load configuration from YAML file with validation."""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        
        # Validate required fields
        required_fields = ['SERVER_URL', 'TARGET_FOLDER', 'FILELIST_URL']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
        
        # Set defaults for optional fields
        config.setdefault('DOWNLOAD_SPEED_LIMIT', 0)  # 0 means no limit
        config.setdefault('MULTITHREADING_THRESHOLD', 10485760)  # 10MB
        config.setdefault('PROGRESS_FILE_MAX_AGE', 86400)  # 1 day
        
        # Validate values
        if not config['SERVER_URL'].endswith('/'):
            config['SERVER_URL'] += '/'
            
        # Ensure TARGET_FOLDER exists
        os.makedirs(config['TARGET_FOLDER'], exist_ok=True)
        
        log_info("Configuration loaded successfully")
        return config
    except Exception as e:
        log_error(f"Error loading configuration: {e}")
        raise

try:
    config = load_config()
    
    SERVER_URL = config['SERVER_URL']
    TARGET_FOLDER = config['TARGET_FOLDER']
    FILELIST_URL = config['FILELIST_URL']
    DOWNLOAD_SPEED_LIMIT = config['DOWNLOAD_SPEED_LIMIT']
    MULTITHREADING_THRESHOLD = config['MULTITHREADING_THRESHOLD']
    PROGRESS_FILE_MAX_AGE = config['PROGRESS_FILE_MAX_AGE']
    
except Exception as e:
    # Provide sensible defaults if config fails to load
    log_error(f"Using default configuration due to error: {e}")
    SERVER_URL = 'https://example.com/'
    TARGET_FOLDER = 'patcher'
    FILELIST_URL = 'https://example.com/patcher.txt'
    DOWNLOAD_SPEED_LIMIT = 0
    MULTITHREADING_THRESHOLD = 10485760
    PROGRESS_FILE_MAX_AGE = 86400