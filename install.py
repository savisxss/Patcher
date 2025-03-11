import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if the Python version is compatible."""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 7):
        print(f"Error: Python 3.7+ is required. Current version: {major}.{minor}")
        return False
    return True

def install_requirements():
    """Install the required packages using pip."""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def setup_directories():
    """Create necessary directories."""
    print("Setting up directories...")
    try:
        os.makedirs("logs", exist_ok=True)
        os.makedirs("patcher", exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directories: {e}")
        return False

def validate_config():
    """Check if the configuration file is valid."""
    print("Validating configuration...")
    if not os.path.exists("config.yaml"):
        print("Warning: config.yaml not found. Creating a sample config...")
        
        sample_config = """SERVER_URL: 'https://example.com/'
TARGET_FOLDER: 'patcher'
FILELIST_URL: 'https://example.com/patcher.txt'
DOWNLOAD_SPEED_LIMIT: 0  # KB/s (0 means no limit)
MULTITHREADING_THRESHOLD: 10485760  # bytes
PROGRESS_FILE_MAX_AGE: 86400 # seconds
"""
        
        try:
            with open("config.yaml", "w") as f:
                f.write(sample_config)
            print("Sample config.yaml created. Please update it with your server details.")
        except Exception as e:
            print(f"Error creating sample config: {e}")
            return False
    
    # Basic validation of the config file
    try:
        import yaml
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        required_keys = ["SERVER_URL", "TARGET_FOLDER", "FILELIST_URL"]
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(f"Error: Missing required configuration keys: {', '.join(missing_keys)}")
            return False
            
        return True
    except ImportError:
        print("Warning: PyYAML not installed. Will validate config after dependencies are installed.")
        return True
    except Exception as e:
        print(f"Error validating config: {e}")
        return False

def create_shortcuts():
    """Create desktop shortcuts based on the platform."""
    system = platform.system()
    print(f"Creating shortcuts for {system}...")
    
    if system == "Windows":
        try:
            # Check if win32com is available
            import win32com.client
            
            # Create Windows shortcut
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, "Patcher.lnk")
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = os.path.abspath("main.py")
            shortcut.WorkingDirectory = os.path.abspath(".")
            shortcut.IconLocation = os.path.abspath("resources/patcher_icon.ico")
            shortcut.save()
            
            print(f"Shortcut created at: {shortcut_path}")
            return True
        except ImportError:
            print("Warning: win32com not installed. Skipping shortcut creation.")
            return True
        except Exception as e:
            print(f"Error creating shortcut: {e}")
            return False
            
    elif system == "Linux":
        try:
            # Create Linux .desktop file
            desktop_file = os.path.expanduser("~/.local/share/applications/patcher.desktop")
            content = f"""[Desktop Entry]
Name=Patcher
Exec=python3 {os.path.abspath("main.py")}
Icon={os.path.abspath("resources/patcher_icon.png")}
Terminal=false
Type=Application
Categories=Utility;
"""
            with open(desktop_file, "w") as f:
                f.write(content)
            
            os.chmod(desktop_file, 0o755)
            print(f"Desktop shortcut created at: {desktop_file}")
            return True
        except Exception as e:
            print(f"Error creating desktop file: {e}")
            return False
            
    elif system == "Darwin":  # macOS
        print("Shortcut creation not supported on macOS yet.")
        return True
        
    return True

def main():
    """Main installation function."""
    print("===== Patcher Installation =====")
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Setup directories
    if not setup_directories():
        return 1
    
    # Install requirements
    if not install_requirements():
        return 1
    
    # Validate configuration
    if not validate_config():
        return 1
    
    # Create shortcuts (optional)
    create_shortcuts()
    
    print("\nInstallation completed successfully!")
    print("You can now run the application with:")
    print(f"  {sys.executable} main.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())