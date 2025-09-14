# Patcher - Tauri + Python

Modern update and patch management system built with Tauri (Rust + Vue.js) frontend and Python backend.

## 🚀 Features

- **Modern UI**: Beautiful Vue.js interface with real-time updates
- **Python Backend**: Reliable Python backend with asyncio for high performance
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Efficient Downloads**: Asynchronous downloads with resume capability
- **File Integrity**: SHA-256 checksum verification
- **Progress Tracking**: Real-time progress updates with detailed logging
- **Configuration Management**: Easy configuration through the UI

## 📋 Requirements

- Python 3.7 or higher
- Node.js 16 or higher
- Rust (if building from source)

## 🔧 Quick Start

### Option 1: Easy Start (Recommended)
Run the start script:
```bash
start.bat
```

### Option 2: Manual Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Start the application:**
   ```bash
   npm run tauri dev
   ```

## 🏗️ Building for Production

To build a production executable:

```bash
npm run tauri build
```

The built executable will be available in `src-tauri/target/release/`.

## ⚙️ How It Works

The application consists of two parts:

1. **Tauri Frontend**: Modern Vue.js interface that runs as a desktop app
2. **Python Backend**: HTTP API server that handles the actual downloading and patching

When you start the application:
1. Tauri app launches and automatically starts the Python backend
2. Backend runs on `localhost:8080` and provides REST API endpoints
3. Frontend communicates with backend via HTTP requests
4. Progress updates are sent via Tauri events for real-time UI updates

## 🔧 Configuration

Configure your settings through the UI:

- **Server URL**: Base URL for downloading files (must end with '/')
- **Target Folder**: Local folder where files will be downloaded
- **File List URL**: URL to the file containing the list of files to download
- **Download Speed Limit**: Maximum download speed in KB/s (0 = unlimited)

Configuration is automatically saved to `config.yaml`.

## 📁 File List Format

The file list should be a text file with each line in the format:
```
path/to/file,sha256-checksum
```

Example:
```
data/config.json,e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
images/logo.png,a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e
```

## 🔍 Logging

Logs are automatically stored in the `logs/` directory:
- `logs/patcher.log`: Application logs with automatic rotation

## 🛠️ Development

### Project Structure
```
├── src/                    # Vue.js frontend
│   ├── App.vue            # Main application component
│   ├── main.ts            # Vue app entry point
│   └── styles.css         # Global styles
├── src-tauri/             # Tauri/Rust backend
│   ├── src/main.rs        # Tauri application logic
│   └── Cargo.toml         # Rust dependencies
├── python_backend.py      # Python API server
├── downloader/            # Python download modules
├── requirements.txt       # Python dependencies
└── package.json          # Node.js dependencies
```

### Available Scripts

- `npm run dev` - Start Vite development server
- `npm run build` - Build Vue.js for production
- `npm run tauri dev` - Start Tauri development mode
- `npm run tauri build` - Build production executable

### Backend API Endpoints

- `GET /health` - Health check
- `GET /config` - Get current configuration
- `POST /config` - Save configuration
- `POST /update` - Start update process
- `GET /status` - Get update status and progress

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## 📝 License

This project is licensed under the MIT License.