from pathlib import Path

from flask import current_app
from flask import url_for

from ..config import PDF_DIR, UPLOAD_DIR
from ..utils.files import unique_filename


def get_upload_dir() -> Path:
    return Path(current_app.config.get("UPLOAD_FOLDER", UPLOAD_DIR))


def get_pdf_dir() -> Path:
    return Path(current_app.config.get("PDF_FOLDER", PDF_DIR))


def ensure_storage_dirs() -> None:
    get_upload_dir().mkdir(parents=True, exist_ok=True)
    get_pdf_dir().mkdir(parents=True, exist_ok=True)


def save_uploaded_file(storage) -> str:
    filename = unique_filename(storage.filename)
    storage.save(get_upload_dir() / filename)
    return filename


def delete_uploaded_file(filename: str) -> None:
    path = get_upload_dir() / filename
    if path.exists():
        path.unlink(missing_ok=True)


def get_uploaded_file_path(filename: str) -> Path:
    return get_upload_dir() / filename


def get_pdf_file_path(filename: str) -> Path:
    return get_pdf_dir() / filename


def get_uploaded_file_url(foto_id: int) -> str:
    return url_for("media.uploaded_file", foto_id=foto_id)


def get_public_uploaded_file_url(token: str, foto_id: int) -> str:
    return url_for("media.public_uploaded_file", token=token, foto_id=foto_id)


def get_pdf_file_url(inventario_id: int) -> str:
    return url_for("media.generated_pdf", inventario_id=inventario_id)
