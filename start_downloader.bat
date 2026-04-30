@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No se encontro el entorno virtual .venv.
    echo Abre PowerShell en esta carpeta y ejecuta:
    echo py -m venv .venv
    echo .\.venv\Scripts\activate
    echo pip install -r requirements.txt
    pause
    exit /b
)

start "Media Downloader Server" /min cmd /c ".venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak >nul

start "" "http://127.0.0.1:8000"