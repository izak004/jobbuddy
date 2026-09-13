@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo No setup found yet. Double-click SETUP.bat first ^(one-time only^).
    pause
    exit /b 1
)

REM Runs the server in its own window (titled "JobBuddy") via run_server.bat, so this
REM launcher window can close right away. If the server crashes, that window stays open
REM (run_server.bat ends with `pause`) so the error is visible instead of just vanishing.
start "JobBuddy" /min run_server.bat

timeout /t 3 >nul
start "" "http://127.0.0.1:5057"
echo JobBuddy is starting in a separate "JobBuddy" window (check your taskbar).
echo This window will close itself shortly — closing it does NOT stop the app.
timeout /t 4 >nul
