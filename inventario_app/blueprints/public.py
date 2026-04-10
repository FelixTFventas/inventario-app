from flask import Blueprint, current_app, render_template, request

from ..models import Inventario, Seccion
from ..services.media_service import get_public_uploaded_file_url
from ..utils.files import is_video_filename


bp = Blueprint("public", __name__)


@bp.route("/publico/<string:token>", endpoint="inventario_publico")
def inventario_publico(token):
    inventario = Inventario.query.filter_by(token=token).first_or_404()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = current_app.config.get("PUBLIC_SECTIONS_PER_PAGE", 10)
    pagination = (
        Seccion.query.filter_by(inventario_id=inventario.id)
        .order_by(Seccion.id.asc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    secciones = pagination.items
    return render_template(
        "inventario_publico.html",
        inventario=inventario,
        secciones=secciones,
        pagination=pagination,
        public_uploaded_file_url=get_public_uploaded_file_url,
        is_video_file=is_video_filename,
    )
