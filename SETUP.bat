@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ================================================
echo   JobBuddy - First-time Setup
echo ================================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python was not found on this computer.
    where winget >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo Couldn't install it automatically ^(winget isn't available^).
        echo Please install Python 3.10 or newer yourself from https://python.org/downloads/
        echo IMPORTANT: check "Add Python to PATH" during install. Then run SETUP.bat again.
        pause
        exit /b 1
    )
    echo Installing Python automatically via winget — this can take a couple of minutes...
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo.
        echo Automatic install didn't complete. Please install Python 3.10+ yourself from
        echo https://python.org/downloads/ ^(check "Add Python to PATH"^), then run SETUP.bat again.
        pause
        exit /b 1
    )
    echo.
    echo Python is installed. Please close this window and double-click SETUP.bat again
    echo ^(Windows needs a fresh window to notice the new install^).
    pause
    exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating a private Python environment for this app...
    python -m venv .venv
)

echo Installing required packages ^(one-time^)...
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Package install failed — check your internet connection and try again.
    pause
    exit /b 1
)

echo Installing the browser component used for one of the job sources ^(one-time, ~115MB^)...
".venv\Scripts\python.exe" -m playwright install chromium
if %errorlevel% neq 0 (
    echo ^(That didn't complete, but everything else still works — that one source will just be skipped.^)
)

echo.
echo ================================================
echo   Setup complete! Launching the app...
echo ================================================
start "JobBuddy" /min run_server.bat
timeout /t 3 >nul
start "" "http://127.0.0.1:5057/setup"

echo.
echo The app is now running in a separate "JobBuddy" window (check your taskbar). This
echo first run will walk you through a short setup form (API key, resume, job preferences)
echo before showing your dashboard.
echo.
echo From now on, use start_dashboard.bat to launch it — you only need SETUP.bat once.
pause
