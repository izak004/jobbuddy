@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" app.py
echo.
echo Server stopped or crashed — if you saw an error above, that's why.
pause
