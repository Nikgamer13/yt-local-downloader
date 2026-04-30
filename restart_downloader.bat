@echo off
cd /d "%~dp0"

timeout /t 3 /nobreak >nul

start "Media Downloader Server" /min cmd /c ".venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000"

exit /b