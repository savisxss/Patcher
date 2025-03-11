@echo off
SETLOCAL EnableDelayedExpansion

echo Patcher - Compilation Script
echo =========================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not in the PATH.
    echo Please install Python from https://www.python.org/downloads/
    exit /b 1
)

REM Check Python version
python --version | findstr /C:"Python 3" >nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python 3 is required.
    echo Current Python version:
    python --version
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo PyInstaller not found. Attempting to install...
    python -m pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install PyInstaller.
        exit /b 1
    )
)

REM Check if all required dependencies are installed
echo Checking requirements...
python -m pip install -r requirements.txt

REM Create build directory
if not exist build mkdir build

REM Clean previous build files
echo Cleaning previous build files...
if exist build\patcher rmdir /S /Q build\patcher
if exist dist rmdir /S /Q dist

REM Copy config
echo Copying configuration...
copy config.yaml dist\ >nul 2>nul

REM Create version file
echo Creating version information...
echo version=1.0.0 > version.txt
echo build_date=%date% >> version.txt
echo build_time=%time% >> version.txt

REM Build the executable
echo Building executable...
pyinstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name Patcher ^
    --icon=resources/patcher_icon.ico ^
    --add-data "version.txt;." ^
    --add-data "config.yaml;." ^
    --hidden-import=aiohttp ^
    --hidden-import=aiofiles ^
    --hidden-import=yaml ^
    --hidden-import=psutil ^
    main.py

REM Check if build was successful
if not exist dist\Patcher.exe (
    echo Build failed. No executable was created.
    exit /b 1
)

REM Create logs directory in the distribution
echo Creating logs directory...
if not exist dist\logs mkdir dist\logs

REM Creating target directory
echo Creating target directory...
if not exist dist\patcher mkdir dist\patcher

echo.
echo Build completed successfully!
echo Executable is located at: dist\Patcher.exe
echo.

ENDLOCAL