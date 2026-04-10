from flask import Blueprint, abort, send_from_directory
from flask_login import login_required

from ..extensions import db
from ..models import Foto
from ..services.access import (
    get_foto_for_current_company_or_404,
    get_inventario_for_current_company_or_404,
)
from ..services.media_service import get_pdf_dir, get_upload_dir


bp = Blueprint("media", __name__)


@bp.route("/media/uploads/<int:foto_id>", endpoint="uploaded_file")
@login_required
def uploaded_file(foto_id):
    foto = get_foto_for_current_company_or_404(foto_id)
    path = get_upload_dir() / foto.archivo
    if not path.is_file():
        return ("", 404)
    return send_from_directory(get_upload_dir(), foto.archivo)


@bp.route(
    "/publico/<string:token>/media/<int:foto_id>", endpoint="public_uploaded_file"
)
def public_uploaded_file(token, foto_id):
    foto = db.session.get(Foto, foto_id)
    if not foto:
        abort(404)
    if foto.seccion.inventario.token != token:
        abort(404)

    path = get_upload_dir() / foto.archivo
    if not path.is_file():
        abort(404)
    return send_from_directory(get_upload_dir(), foto.archivo)


@bp.route("/media/pdfs/<int:inventario_id>", endpoint="generated_pdf")
@login_required
def generated_pdf(inventario_id):
    inventario = get_inventario_for_current_company_or_404(inventario_id)
    filename = f"inventario_{inventario.id}.pdf"
    path = get_pdf_dir() / filename
    if not path.is_file():
        return ("", 404)
    return send_from_directory(get_pdf_dir(), filename)
