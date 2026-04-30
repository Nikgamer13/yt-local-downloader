import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import quote, urlparse
import json
import threading
from urllib.request import urlopen

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
DOWNLOAD_DIR = BASE_DIR / "downloads"
BACKUP_DIR = BASE_DIR / "backups"
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"
UPDATE_FILE = BASE_DIR / ".last_ytdlp_update"
RESTART_SCRIPT = BASE_DIR / "restart_downloader.bat"

# Recomendado:
# False = usa versión local congelada.
# True = actualiza yt-dlp automáticamente máximo una vez al día.
AUTO_UPDATE_YTDLP = False

DOWNLOAD_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Media Local Downloader")


def get_ytdlp_version() -> str:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import yt_dlp.version as v; print(v.__version__)",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "No instalado"

def version_to_tuple(version: str) -> tuple:
    """
    Convierte versiones tipo 2026.03.17 a una tupla comparable.
    """
    try:
        return tuple(int(part) for part in version.split("."))
    except Exception:
        return tuple()


def get_latest_ytdlp_version() -> str:
    """
    Consulta PyPI para saber la última versión disponible de yt-dlp.
    """
    try:
        with urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        return data["info"]["version"]

    except Exception:
        return "No se pudo comprobar"


def restart_app_soon():
    """
    Lanza el script de reinicio y luego cierra el servidor actual.
    """
    def delayed_restart():
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", str(RESTART_SCRIPT)],
                cwd=BASE_DIR,
                shell=False,
            )
        except Exception as error:
            print(f"No se pudo lanzar el reinicio automático: {error}")

        time.sleep(1)
        os._exit(0)

    thread = threading.Thread(target=delayed_restart, daemon=True)
    thread.start()

def unload_ytdlp_modules():
    """
    Si restauras o actualizas yt-dlp mientras la app está abierta,
    quitamos yt_dlp de la memoria para que el próximo uso cargue la versión instalada.
    """
    modules_to_delete = [
        module_name
        for module_name in sys.modules
        if module_name == "yt_dlp" or module_name.startswith("yt_dlp.")
    ]

    for module_name in modules_to_delete:
        del sys.modules[module_name]


def update_ytdlp_if_needed():
    one_day_seconds = 24 * 60 * 60
    now = time.time()

    if UPDATE_FILE.exists():
        try:
            last_update = float(UPDATE_FILE.read_text(encoding="utf-8"))

            if now - last_update < one_day_seconds:
                return
        except ValueError:
            pass

    try:
        print("Revisando actualización de yt-dlp...")

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            check=True,
        )

        unload_ytdlp_modules()
        UPDATE_FILE.write_text(str(now), encoding="utf-8")
        print("yt-dlp actualizado correctamente.")

    except Exception as error:
        print(f"No se pudo actualizar yt-dlp: {error}")


def is_allowed_media_url(url: str) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().split(":")[0]

    allowed_domains = {
        # YouTube
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",

        # Instagram
        "instagram.com",
        "www.instagram.com",

        # TikTok
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
        "vt.tiktok.com",
    }

    return parsed.scheme in {"http", "https"} and domain in allowed_domains


def safe_file_from_folder(folder: Path, filename: str) -> Path:
    file_path = (folder / filename).resolve()
    folder_path = folder.resolve()

    if folder_path not in file_path.parents:
        raise HTTPException(status_code=400, detail="Archivo inválido.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    return file_path


def safe_extract_zip(zip_path: Path, extract_to: Path):
    extract_to_resolved = extract_to.resolve()

    with zipfile.ZipFile(zip_path, "r") as zip_file:
        for member in zip_file.infolist():
            target_path = (extract_to / member.filename).resolve()

            if extract_to_resolved not in target_path.parents and target_path != extract_to_resolved:
                raise HTTPException(
                    status_code=400,
                    detail="El zip tiene rutas inválidas. No se restauró.",
                )

        zip_file.extractall(extract_to)


def get_video_height(video_path: Path) -> int | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=height",
                "-of",
                "csv=p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        value = result.stdout.strip()

        if not value:
            return None

        return int(value)

    except Exception:
        return None


def compress_video_to_height(video_path: Path, target_height: int) -> bool:
    """
    Si el video quedó con más altura que la solicitada,
    lo recomprime a esa altura con FFmpeg.

    Retorna True si comprimió.
    Retorna False si no era necesario.
    """
    current_height = get_video_height(video_path)

    if current_height is None:
        raise HTTPException(
            status_code=500,
            detail="No pude detectar la resolución del video con ffprobe.",
        )

    if current_height <= target_height:
        return False

    temp_path = video_path.with_name(
        f"{video_path.stem}.__compressed__{video_path.suffix}"
    )

    if target_height <= 240:
        crf = "32"
        audio_bitrate = "64k"
    elif target_height <= 480:
        crf = "30"
        audio_bitrate = "96k"
    else:
        crf = "28"
        audio_bitrate = "128k"

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"scale=-2:{target_height}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                crf,
                "-c:a",
                "aac",
                "-b:a",
                audio_bitrate,
                str(temp_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        temp_path.replace(video_path)
        return True

    except subprocess.CalledProcessError as error:
        if temp_path.exists():
            temp_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo comprimir el video con FFmpeg.\n"
                + (error.stderr or error.stdout or "Sin detalle.")
            ),
        )


@app.get("/", response_class=HTMLResponse)
def home():
    if AUTO_UPDATE_YTDLP:
        update_ytdlp_if_needed()

    index_path = STATIC_DIR / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=500, detail="No existe static/index.html")

    return index_path.read_text(encoding="utf-8")


@app.get("/ytdlp-info")
def ytdlp_info():
    installed_version = get_ytdlp_version()
    latest_version = get_latest_ytdlp_version()

    update_available = False

    if (
        installed_version != "No instalado"
        and latest_version != "No se pudo comprobar"
    ):
        update_available = version_to_tuple(latest_version) > version_to_tuple(installed_version)

    return {
        "version": installed_version,
        "latest_version": latest_version,
        "update_available": update_available,
        "auto_update": AUTO_UPDATE_YTDLP,
        "mode": "Congelado / actualización manual"
        if not AUTO_UPDATE_YTDLP
        else "Actualización automática diaria",
    }


@app.post("/update-ytdlp")
def update_ytdlp_now():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            capture_output=True,
            text=True,
            check=True,
        )

        unload_ytdlp_modules()
        UPDATE_FILE.write_text(str(time.time()), encoding="utf-8")

        new_version = get_ytdlp_version()

        restart_app_soon()

        return {
            "message": "yt-dlp actualizado correctamente. La app se reiniciará automáticamente.",
            "version": new_version,
            "output": result.stdout[-1500:],
            "restart": True,
        }

    except subprocess.CalledProcessError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo actualizar yt-dlp.\n"
                + (error.stderr or error.stdout or "Sin detalle.")
            ),
        )


@app.get("/backups")
def list_backups():
    backups = []

    for file in BACKUP_DIR.glob("*.zip"):
        stat = file.stat()

        backups.append(
            {
                "filename": file.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(stat.st_mtime),
                ),
                "download_url": f"/backup-file/{quote(file.name)}",
            }
        )

    backups.sort(key=lambda item: item["modified"], reverse=True)

    return {"backups": backups}


@app.post("/backup-dependencies")
def backup_dependencies():
    build_dir = BACKUP_DIR / "_backup_build"
    temp_vendor_dir = build_dir / "vendor"
    temp_requirements = build_dir / "requirements.txt"

    try:
        if build_dir.exists():
            shutil.rmtree(build_dir)

        temp_vendor_dir.mkdir(parents=True, exist_ok=True)

        # 1. Guardar versiones exactas actuales.
        freeze_result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True,
        )

        requirements_text = freeze_result.stdout

        REQUIREMENTS_FILE.write_text(requirements_text, encoding="utf-8")
        temp_requirements.write_text(requirements_text, encoding="utf-8")

        # 2. Descargar instaladores locales a una carpeta temporal.
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "-r",
                str(temp_requirements),
                "-d",
                str(temp_vendor_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # 3. Crear .zip con requirements.txt + vendor/.
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        version = get_ytdlp_version().replace(".", "-")
        zip_name = f"backup-ytdlp-{version}-{timestamp}.zip"
        zip_path = BACKUP_DIR / zip_name

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(temp_requirements, arcname="requirements.txt")

            for file in temp_vendor_dir.iterdir():
                if file.is_file():
                    zip_file.write(file, arcname=f"vendor/{file.name}")

        size_mb = zip_path.stat().st_size / (1024 * 1024)

        return {
            "message": "Respaldo creado correctamente.",
            "filename": zip_name,
            "size_mb": round(size_mb, 2),
            "download_url": f"/backup-file/{quote(zip_name)}",
        }

    except subprocess.CalledProcessError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo crear el respaldo.\n"
                + (error.stderr or error.stdout or "Sin detalle.")
            ),
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo crear el respaldo. Error: {str(error)}",
        )
    finally:
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)


@app.post("/restore-backup")
def restore_backup(filename: str = Form(...)):
    zip_path = safe_file_from_folder(BACKUP_DIR, filename)
    restore_dir = BACKUP_DIR / "_restore_tmp"

    try:
        if restore_dir.exists():
            shutil.rmtree(restore_dir)

        restore_dir.mkdir(parents=True, exist_ok=True)

        safe_extract_zip(zip_path, restore_dir)

        restored_requirements = restore_dir / "requirements.txt"
        restored_vendor = restore_dir / "vendor"

        if not restored_requirements.exists() or not restored_vendor.exists():
            raise HTTPException(
                status_code=400,
                detail="El respaldo no contiene requirements.txt y vendor/.",
            )

        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(restored_vendor),
                "-r",
                str(restored_requirements),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        shutil.copy(restored_requirements, REQUIREMENTS_FILE)

        unload_ytdlp_modules()

        return {
            "message": "Respaldo restaurado correctamente.",
            "version": get_ytdlp_version(),
        }

    except subprocess.CalledProcessError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo restaurar el respaldo.\n"
                + (error.stderr or error.stdout or "Sin detalle.")
            ),
        )
    finally:
        if restore_dir.exists():
            shutil.rmtree(restore_dir, ignore_errors=True)


@app.post("/delete-backup")
def delete_backup(filename: str = Form(...)):
    zip_path = safe_file_from_folder(BACKUP_DIR, filename)

    try:
        zip_path.unlink()

        return {"message": "Respaldo eliminado correctamente."}

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo eliminar el respaldo. Error: {str(error)}",
        )


@app.post("/open-backup-folder")
def open_backup_folder():
    try:
        if os.name == "nt":
            os.startfile(BACKUP_DIR)
        else:
            subprocess.Popen(["xdg-open", str(BACKUP_DIR)])

        return {"message": "Carpeta de respaldos abierta."}

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo abrir la carpeta. Error: {str(error)}",
        )


@app.post("/download")
def download(
    url: str = Form(...),
    mode: str = Form(...),
    quality: str = Form("480"),
):
    if not is_allowed_media_url(url):
        raise HTTPException(
            status_code=400,
            detail="Por seguridad, esta versión solo acepta links de YouTube, Instagram o TikTok.",
        )

    if mode not in {"audio", "video"}:
        raise HTTPException(status_code=400, detail="Modo inválido.")

    if mode == "video":
        valid_qualities = {"144", "240", "360", "480", "720", "1080", "best"}

        if quality not in valid_qualities:
            raise HTTPException(status_code=400, detail="Calidad inválida.")

        format_label = "video-best" if quality == "best" else f"video-{quality}p"
    else:
        format_label = "audio"

    common_options = {
        "outtmpl": str(
            DOWNLOAD_DIR / f"%(title).120B [%(id)s] [{format_label}].%(ext)s"
        ),
        "noplaylist": True,
        "restrictfilenames": True,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "overwrites": False,
    }

    if mode == "audio":
        ydl_options = {
            **common_options,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    else:
        if quality == "best":
            selected_format = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best"
        else:
            selected_format = (
                f"bv*[height<={quality}][ext=mp4]+ba[ext=m4a]/"
                f"b[height<={quality}][ext=mp4]/"
                f"bv*[ext=mp4]+ba[ext=m4a]/"
                f"b[ext=mp4]/"
                f"best"
            )

        ydl_options = {
            **common_options,
            "format": selected_format,
            "merge_output_format": "mp4",
        }

    try:
        from yt_dlp import YoutubeDL

        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=True)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo descargar. Error: {str(error)}",
        )

    video_id = info.get("id")

    if not video_id:
        raise HTTPException(
            status_code=500,
            detail="La descarga terminó, pero no pude identificar el video.",
        )

    matching_files = [
        file
        for file in DOWNLOAD_DIR.iterdir()
        if file.is_file()
        and f"[{video_id}]" in file.name
        and f"[{format_label}]" in file.name
    ]

    if mode == "audio":
        matching_files = [
            file for file in matching_files if file.suffix.lower() == ".mp3"
        ]
    else:
        matching_files = [
            file for file in matching_files if file.suffix.lower() == ".mp4"
        ]

    if not matching_files:
        raise HTTPException(
            status_code=500,
            detail="La descarga terminó, pero no encontré el archivo final.",
        )

    downloaded_file = max(matching_files, key=lambda file: file.stat().st_mtime)

    compressed = False

    if mode == "video" and quality != "best":
        compressed = compress_video_to_height(downloaded_file, int(quality))

    return {
        "message": "Descarga completada.",
        "filename": downloaded_file.name,
        "download_url": f"/file/{quote(downloaded_file.name)}",
        "compressed": compressed,
        "quality": quality,
    }


@app.get("/file/{filename}")
def get_file(filename: str):
    file_path = safe_file_from_folder(DOWNLOAD_DIR, filename)

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@app.get("/backup-file/{filename}")
def get_backup_file(filename: str):
    file_path = safe_file_from_folder(BACKUP_DIR, filename)

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/zip",
    )