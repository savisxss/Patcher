# Patcher

Patcher is a comprehensive update and patch management system designed to streamline the process of applying updates to software. It includes a file manager, updater, and a graphical user interface for ease of use.

## Features

- **Automatic Updates**: Easily configure Patcher to automatically check for and apply updates.
- **File Hashing**: Ensure the integrity of your files by generating and verifying file checksums.
- **GUI Support**: A user-friendly graphical interface to manage and apply patches.
- **Logging**: Detailed logs for tracking updates and error handling.

## Installation

To use Patcher, you'll need to have Python installed on your system. You can download Python [here](https://www.python.org/downloads/).

After installing Python, clone the repository to your local machine:
git clone https://github.com/savisxss/Patcher.git
cd Patcher

Install the required dependencies:
pip install -r requirements.txt

## Usage

To start Patcher, run the `main.py` script:
python main.py

## Building an Executable

To build Patcher into a standalone executable, you can use PyInstaller. Ensure you have PyInstaller installed:
pip install pyinstaller

Run the provided batch script to compile the executable:
compile_to_exe.bat

This will generate an executable in the `dist` directory.