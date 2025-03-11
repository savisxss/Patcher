# Patcher

Patcher is a high-performance update and patch management system designed to streamline the process of applying updates to software. It features an efficient file manager, asynchronous updater, and an intuitive graphical user interface.

## 🚀 Features

- **Efficient Asynchronous Downloads**: Uses asynchronous I/O and multithreading for optimal performance
- **Resumable Downloads**: Automatically resumes interrupted downloads to save time and bandwidth
- **File Integrity Verification**: Ensures the integrity of downloaded files through SHA-256 checksum verification
- **Bandwidth Control**: Configurable download speed limits to prevent network saturation
- **Modern GUI**: User-friendly interface with progress tracking and detailed status reports
- **Robust Logging**: Comprehensive logging system with rotating file handlers to track operations
- **Cross-Platform**: Works on Windows, macOS, and Linux

## 📋 Requirements

- Python 3.7 or higher
- Required packages (automatically installed):
  - `aiohttp`: For asynchronous HTTP requests
  - `aiofiles`: For asynchronous file operations
  - `PyYAML`: For configuration parsing
  - `PyQt5`: For the graphical user interface
  - `psutil`: For system monitoring functions

## 🔧 Installation

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/savisxss/Patcher.git
   cd Patcher
   ```

2. Run the installer script:
   ```bash
   python install.py
   ```

3. Update the `config.yaml` file with your server details

4. Run the application:
   ```bash
   python main.py
   ```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/savisxss/Patcher.git
   cd Patcher
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Update the `config.yaml` file with your server details

4. Create necessary directories:
   ```bash
   mkdir -p logs patcher
   ```

5. Run the application:
   ```bash
   python main.py
   ```

## 🖥️ Building an Executable

To build Patcher into a standalone executable, you can use the included batch script:

### Windows

```bash
compile_to_exe.bat
```

This will generate an executable in the `dist` directory.

### macOS/Linux

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name Patcher --add-data "config.yaml:." main.py
```

## ⚙️ Configuration

The application uses a `config.yaml` file with the following settings:

```yaml
SERVER_URL: 'https://your-server.com/'
TARGET_FOLDER: 'patcher'
FILELIST_URL: 'https://your-server.com/patcher.txt'
DOWNLOAD_SPEED_LIMIT: 0  # KB/s (0 means no limit)
MULTITHREADING_THRESHOLD: 10485760  # bytes (10MB)
PROGRESS_FILE_MAX_AGE: 86400  # seconds (24 hours)
```

### Configuration Options

- **SERVER_URL**: Base URL for downloading files (must end with a '/')
- **TARGET_FOLDER**: Local folder where downloaded files will be stored
- **FILELIST_URL**: URL to the file containing the list of files to download
- **DOWNLOAD_SPEED_LIMIT**: Maximum download speed in KB/s (0 = unlimited)
- **MULTITHREADING_THRESHOLD**: File size threshold for enabling multithreaded downloads
- **PROGRESS_FILE_MAX_AGE**: Maximum age of progress files before automatic cleanup

## 📁 File List Format

The file list should be a text file with each line in the format:

```
path/to/file,sha256-checksum
```

For example:
```
data/config.json,e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
images/logo.png,a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e
```

You can generate this file with the included tool:

```bash
python generate_patch_filelist.py --target /path/to/files --output patcher.txt
```

## 🔍 Logging

Logs are stored in the `logs` directory with automatic rotation:
- `logs/patcher.log`: Main application log
- `patch_generator.log`: Generated when creating file lists

## 👥 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to improve the application.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.