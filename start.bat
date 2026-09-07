@echo off
title Nano Banana Pro - Image Translator
echo ===================================================
echo     Nano Banana Pro - Image Translator Server
echo ===================================================
echo.

:: Check if virtual environment exists, if not use global python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo [1/3] Installing/verifying requirements...
pip install -r requirements.txt --quiet

echo.
echo [2/3] Starting FastAPI Server on http://localhost:8000 ...
start "" http://localhost:8000

echo [3/3] Running bridge server...
python main.py

pause
