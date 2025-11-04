@echo off
echo ========================================
echo CSV Massive Data Analyzer
echo ========================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo [ERROR] Virtual environment not found
    echo.
    echo Please run instalar.bat first to set up the application
    echo.
    pause
    exit /b 1
)

echo Starting application...
echo.
echo The application will open in your default web browser
echo.
echo To stop the application, press Ctrl+C in this window
echo.

REM Activate virtual environment and run Streamlit
call venv\Scripts\activate.bat
streamlit run app.py

pause

