from flask import Blueprint, abort, send_from_directory
from flask_login import login_required

from ..services.media_service import get_pdf_dir, get_upload_dir


bp = Blueprint("media", __name__)


@bp.route("/media/uploads/<path:filename>", endpoint="uploaded_file")
def uploaded_file(filename):
    path = get_upload_dir() / filename
    if not path.is_file():
        abort(404)
    return send_from_directory(get_upload_dir(), filename)


@bp.route("/media/pdfs/<path:filename>", endpoint="generated_pdf")
@login_required
def generated_pdf(filename):
    path = get_pdf_dir() / filename
    if not path.is_file():
        abort(404)
    return send_from_directory(get_pdf_dir(), filename)
