@echo off
echo ========================================
echo CSV Massive Data Analyzer - Installation
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed
python --version
echo.

REM Check Python version (basic check)
echo Checking Python version...
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Python 3.8 or higher is recommended
    echo Current version might not be compatible
    echo.
)

REM Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Removing old one...
    rmdir /s /q venv
)

python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    echo.
    pause
    exit /b 1
)

echo [OK] Virtual environment created
echo.

REM Activate virtual environment and install dependencies
echo Installing dependencies...
echo This may take a few minutes...
echo.

call venv\Scripts\activate.bat

python -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
)

pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    echo.
    echo Please check your internet connection and try again
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo To run the application, execute: ejecutar.bat
echo.
pause

