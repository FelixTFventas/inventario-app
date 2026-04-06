from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..models import Foto, Inmueble, Inventario, Seccion
from ..services.access import (
    company_required,
    get_effective_company,
    get_effective_company_id,
    require_edit_permission,
    user_is_superadmin,
)
from ..utils.dates import parse_iso_date


bp = Blueprint("dashboard", __name__)


@bp.route("/", endpoint="index")
@login_required
def index():
    if user_is_superadmin(current_user) and not get_effective_company():
        return redirect(url_for("superadmin.superadmin_empresas"))

    company_required()
    search_query = request.args.get("q", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = current_app.config.get("DASHBOARD_PER_PAGE", 12)
    company_id = get_effective_company_id()

    base_query = Inmueble.query.filter_by(empresa_id=company_id)
    if search_query:
        search_pattern = f"%{search_query}%"
        base_query = base_query.filter(
            or_(
                Inmueble.direccion.ilike(search_pattern),
                Inmueble.propietario.ilike(search_pattern),
                Inmueble.inventarios.any(Inventario.nombre.ilike(search_pattern)),
            )
        )

    pagination = base_query.order_by(Inmueble.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    inmuebles = pagination.items
    all_inmueble_rows = (
        db.session.query(Inmueble.id).filter_by(empresa_id=company_id).all()
    )
    inmueble_ids = [inmueble_id for (inmueble_id,) in all_inmueble_rows]

    total_inmuebles = pagination.total
    total_inventarios = (
        Inventario.query.filter(Inventario.inmueble_id.in_(inmueble_ids)).count()
        if inmueble_ids
        else 0
    )
    total_fotos = (
        Foto.query.join(Seccion)
        .join(Inventario)
        .join(Inmueble)
        .filter(Inmueble.empresa_id == company_id)
        .count()
    )

    return render_template(
        "index.html",
        total_inmuebles=total_inmuebles,
        total_inventarios=total_inventarios,
        total_fotos=total_fotos,
        search_query=search_query,
        inmuebles=inmuebles,
        pagination=pagination,
    )


@bp.route("/crear", methods=["POST"], endpoint="crear")
@login_required
def crear():
    company_required()
    require_edit_permission()
    company_id = get_effective_company_id()

    direccion = request.form.get("direccion", "").strip()
    propietario = request.form.get("propietario", "").strip()
    fecha = parse_iso_date(request.form.get("fecha", ""))

    if not direccion or not propietario or not fecha:
        flash("Completa direccion, propietario y fecha.", "error")
        return redirect(url_for("dashboard.index"))

    nuevo = Inmueble(
        direccion=direccion,
        propietario=propietario,
        fecha_recepcion=fecha,
        empresa_id=company_id,
    )
    db.session.add(nuevo)
    db.session.commit()
    current_app.logger.info(
        "inmueble_created empresa_id=%s inmueble_id=%s", company_id, nuevo.id
    )
    flash("Inmueble creado correctamente.", "success")
    return redirect(url_for("dashboard.index"))
