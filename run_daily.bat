@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" fetch_jobs.py >> "%~dp0data\fetch_log.txt" 2>&1
