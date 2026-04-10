import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

from ..constants import ALLOWED_EXTENSIONS

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def unique_filename(filename: str) -> str:
    safe = secure_filename(filename)
    ext = safe.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"


def is_video_filename(filename: str) -> bool:
    return Path(filename).suffix.lower().lstrip(".") in VIDEO_EXTENSIONS


def validate_uploaded_file(file_storage) -> str | None:
    filename = file_storage.filename or ""
    if not allowed_file(filename):
        return f"Archivo no permitido: {filename}"

    ext = Path(filename).suffix.lower().lstrip(".")
    mimetype = (file_storage.mimetype or "").lower()
    if ext in IMAGE_EXTENSIONS and not mimetype.startswith("image/"):
        return f"El archivo no coincide con un formato de imagen valido: {filename}"
    if ext in VIDEO_EXTENSIONS and not mimetype.startswith("video/"):
        return f"El archivo no coincide con un formato de video valido: {filename}"
    return None
