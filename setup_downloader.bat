@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================
echo  Media Local Downloader - Setup
echo ============================================
echo.

set "PYTHON_CMD="

call :detect_python

if "!PYTHON_CMD!"=="" (
    echo No se encontro Python.
    echo.

    choice /C SN /M "Quieres intentar instalar Python 3.12 con winget"
    if errorlevel 2 (
        echo.
        echo Instalacion cancelada.
        echo Instala Python 3.10 o superior manualmente y vuelve a ejecutar este archivo.
        pause
        exit /b 1
    )

    call :check_winget

    echo.
    echo Instalando Python 3.12 con winget...
    winget install --id Python.Python.3.12 -e

    if errorlevel 1 (
        echo.
        echo ERROR: No se pudo instalar Python con winget.
        echo Instala Python manualmente desde python.org y vuelve a ejecutar este setup.
        pause
        exit /b 1
    )

    echo.
    echo Reintentando detectar Python...
    call :detect_python

    if "!PYTHON_CMD!"=="" (
        echo.
        echo Python parece haberse instalado, pero esta ventana aun no lo detecta.
        echo Cierra esta ventana, abre una nueva y ejecuta setup_downloader.bat otra vez.
        pause
        exit /b 1
    )
)

echo Python encontrado:
!PYTHON_CMD! --version
echo.

echo Revisando version minima de Python...
!PYTHON_CMD! -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul

if errorlevel 1 (
    echo.
    echo ERROR: Tu version de Python es menor a 3.10.
    echo Instala Python 3.10 o superior y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo.
    echo ERROR: No se encontro requirements.txt en esta carpeta.
    echo Asegurate de ejecutar este archivo desde la carpeta del proyecto.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual .venv...
    !PYTHON_CMD! -m venv .venv

    if errorlevel 1 (
        echo.
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo Entorno virtual .venv ya existe.
)

echo.
echo Actualizando pip dentro de .venv...
".venv\Scripts\python.exe" -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo actualizar pip.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias desde requirements.txt...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias.
    pause
    exit /b 1
)

echo.
echo Creando carpetas necesarias...
if not exist "downloads" mkdir downloads
if not exist "backups" mkdir backups

echo.
echo Revisando FFmpeg...
where ffmpeg >nul 2>nul

if errorlevel 1 (
    echo.
    echo No se encontro FFmpeg en el PATH.
    echo.
    echo FFmpeg es necesario para:
    echo - convertir audio a MP3
    echo - unir video y audio
    echo - comprimir videos
    echo.

    choice /C SN /M "Quieres intentar instalar FFmpeg con winget"
    if errorlevel 2 (
        echo.
        echo Saltando instalacion de FFmpeg.
        echo La app puede abrir, pero algunas funciones pueden fallar.
        goto setup_done
    )

    call :check_winget

    echo.
    echo Instalando FFmpeg con winget...
    winget install --id Gyan.FFmpeg -e

    if errorlevel 1 (
        echo.
        echo ADVERTENCIA: No se pudo instalar FFmpeg con winget.
        echo Puedes instalarlo manualmente despues.
        goto setup_done
    )

    echo.
    echo Reintentando detectar FFmpeg...
    where ffmpeg >nul 2>nul

    if errorlevel 1 (
        echo.
        echo FFmpeg parece haberse instalado, pero esta ventana aun no lo detecta.
        echo Cierra esta ventana y abre start_downloader.bat nuevamente.
    ) else (
        echo FFmpeg encontrado correctamente.
    )
) else (
    echo FFmpeg encontrado correctamente.
)

:setup_done
echo.
echo ============================================
echo  Setup completado
echo ============================================
echo.
echo Ahora puedes abrir la app con:
echo start_downloader.bat
echo.

pause
exit /b 0


:detect_python
set "PYTHON_CMD="

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)

exit /b 0


:check_winget
where winget >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: No se encontro winget en este equipo.
    echo No se puede instalar automaticamente.
    echo Instala el requisito manualmente y vuelve a ejecutar setup_downloader.bat.
    pause
    exit /b 1
)

exit /b 0