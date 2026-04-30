# Media Local Downloader

Aplicación web local para descargar audio y video desde enlaces compatibles usando **yt-dlp** y **FFmpeg**.

El proyecto está pensado para ejecutarse en el propio computador, sin necesidad de subir la app a internet ni usar un dominio.

## Funcionalidades

- Descarga de audio en formato MP3.
- Descarga de video en formato MP4.
- Selección de calidad de video:
  - 144p
  - 240p
  - 360p
  - 480p
  - 720p
  - 1080p
  - Mejor disponible
- Compresión automática con FFmpeg si la calidad seleccionada no existe.
- Compatibilidad inicial con:
  - YouTube
  - Instagram
  - TikTok
  - X / Twitter
- Modo congelado para usar una versión local estable de yt-dlp.
- Detección de actualización disponible.
- Actualización manual de yt-dlp.
- Creación de respaldos `.zip` de dependencias.
- Restauración de respaldos anteriores.
- Eliminación de respaldos antiguos.
- Botón para abrir la carpeta de descargas.
- Botón para abrir la carpeta de respaldos.
- Reinicio automático de la app después de actualizar yt-dlp.
- Interfaz web local desde el navegador.

## Requisitos

Antes de usar la app, necesitas tener instalado:

- Python 3.10 o superior.
- Git.
- FFmpeg.

Para comprobar que FFmpeg está instalado correctamente:

```bash
ffmpeg -version
```

Si aparece información de versión, FFmpeg está funcionando.

## Instalación

Clona el repositorio:

```bash
git clone https://github.com/Nikgamer13/yt-local-downloader.git
cd yt-local-downloader
```

Crea un entorno virtual:

```bash
py -m venv .venv
```

Activa el entorno virtual en Windows:

```bash
.\.venv\Scripts\activate
```

Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Uso

Puedes iniciar la app ejecutando:

```bash
start_downloader.bat
```

La app abrirá automáticamente el navegador en:

```txt
http://127.0.0.1:8000
```

También puedes iniciarla manualmente con:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

## Estructura del proyecto

```txt
yt-local-downloader/
│
├─ app.py
├─ requirements.txt
├─ README.md
├─ start_downloader.bat
├─ restart_downloader.bat
├─ .gitignore
│
├─ static/
│  ├─ index.html
│  └─ styles.css
│
├─ downloads/
│  └─ archivos descargados
│
└─ backups/
   └─ respaldos locales
```

## Carpetas importantes

### `downloads/`

Aquí se guardan los audios y videos descargados.

Esta carpeta no se sube a GitHub.

### `backups/`

Aquí se guardan los respaldos `.zip` de dependencias.

Estos respaldos sirven para volver a una versión anterior funcional de yt-dlp si una actualización deja de funcionar correctamente.

Esta carpeta tampoco se sube a GitHub.

### `static/`

Aquí están los archivos de la interfaz web:

- `index.html`
- `styles.css`

## Respaldos

La app permite crear respaldos `.zip` de las dependencias instaladas.

Esto sirve para guardar una versión funcional del proyecto y restaurarla más adelante si algo falla después de actualizar.

Desde la interfaz puedes:

- Crear un respaldo.
- Descargar una copia del respaldo.
- Restaurar un respaldo anterior.
- Eliminar respaldos antiguos.
- Abrir la carpeta de respaldos.

## Actualización de yt-dlp

Por defecto, la app usa un modo congelado/manual.

Esto significa que yt-dlp no se actualiza automáticamente al abrir la app. La razón es evitar que una actualización rompa una versión que ya estaba funcionando bien.

Desde la interfaz puedes revisar si hay una versión nueva disponible y actualizar manualmente.

Después de actualizar, la app intenta reiniciarse automáticamente y recargar la pestaña actual.

## Restaurar una versión anterior

Si actualizas yt-dlp y la nueva versión falla, puedes restaurar un respaldo desde la sección de respaldos guardados.

Flujo recomendado:

```txt
Crear respaldo cuando todo funciona
↓
Actualizar yt-dlp solo cuando quieras probar
↓
Si algo falla, restaurar el respaldo anterior
```

## Compatibilidad

La app acepta inicialmente enlaces de:

- YouTube
- Instagram
- TikTok
- X / Twitter

yt-dlp puede soportar muchos otros sitios, pero esta app usa una lista permitida para mantener el funcionamiento más controlado.

Algunos enlaces pueden fallar si:

- El contenido es privado.
- El contenido requiere iniciar sesión.
- El sitio cambió su funcionamiento.
- El video fue eliminado.
- Hay restricciones por región.
- yt-dlp necesita una actualización.

## Uso responsable

Esta herramienta está pensada para uso personal y local.

Úsala solo con contenido propio, contenido con permiso o material que tengas derecho a descargar.

El proyecto no está pensado para publicarse como servicio abierto en internet.

## Tecnologías usadas

- Python
- FastAPI
- yt-dlp
- FFmpeg
- HTML
- CSS
- JavaScript

## Notas

Este proyecto nació como una app local simple para usar yt-dlp desde una interfaz web más cómoda.

La idea principal es mantenerlo práctico, fácil de ejecutar y con respaldo local para evitar depender completamente de actualizaciones externas.