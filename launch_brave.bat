@echo off
title Launch Brave for Google Flow
echo ===================================================
echo     Launching Brave with Remote Debugging (9222)
echo ===================================================
echo.

set "BRAVE_BIN=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

if not exist "%BRAVE_BIN%" (
    if exist "%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe" (
        set "BRAVE_BIN=%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"
    ) else if exist "C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe" (
        set "BRAVE_BIN=C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
    )
)

if not exist "%BRAVE_BIN%" (
    echo [ERROR] Brave Browser was not found at "%BRAVE_BIN%".
    pause
    exit /b 1
)

echo Found Brave at: "%BRAVE_BIN%"
echo Starting Brave with debugging port 9222...
start "" "%BRAVE_BIN%" --remote-debugging-port=9222 --user-data-dir="C:\brave-flow-profile" "https://labs.google/fx/tools/flow"

echo.
echo [DONE] Brave is running. Please sign into your Google account in that window.
timeout /t 3 >nul
