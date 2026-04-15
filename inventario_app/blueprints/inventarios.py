import base64
import binascii
import re
import uuid

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from ..extensions import db
from ..models import Firma, Inventario, Seccion
from ..services.access import (
    get_inmueble_for_current_company_or_404,
    get_inventario_for_current_company_or_404,
    require_edit_permission,
)
from ..services.media_service import get_pdf_file_url
from ..services.pdf_service import build_inventory_pdf
from ..utils.dates import parse_iso_date


bp = Blueprint("inventarios", __name__)


@bp.route("/crear_inventario/<int:id>", methods=["POST"], endpoint="crear_inventario")
@login_required
def crear_inventario(id):
    require_edit_permission()
    inmueble = get_inmueble_for_current_company_or_404(id)
    nombre = request.form.get("nombre", "").strip()
    fecha = parse_iso_date(request.form.get("fecha", ""))

    if not nombre or not fecha:
        flash("Debes indicar nombre y fecha del inventario.", "error")
        return redirect(url_for("inmuebles.ver_inmueble", id=id))

    nuevo = Inventario(
        inmueble_id=inmueble.id,
        nombre=nombre,
        fecha=fecha,
        token=str(uuid.uuid4()),
    )
    db.session.add(nuevo)
    db.session.flush()

    for nombre_seccion in [
        "Fachada",
        "Sala",
        "Comedor",
        "Cocina",
        "Baños",
        "Habitación principal",
        "Habitación auxiliar",
    ]:
        db.session.add(Seccion(inventario_id=nuevo.id, nombre=nombre_seccion))

    db.session.commit()
    current_app.logger.info(
        "inventario_created inmueble_id=%s inventario_id=%s", inmueble.id, nuevo.id
    )
    flash("Inventario creado correctamente.", "success")
    return redirect(url_for("inmuebles.ver_inmueble", id=id))


@bp.route("/inventario/<int:id>", endpoint="ver_inventario")
@login_required
def ver_inventario(id):
    inventario = get_inventario_for_current_company_or_404(id)
    secciones = (
        Seccion.query.filter_by(inventario_id=id).order_by(Seccion.id.asc()).all()
    )
    return render_template(
        "inventario.html", inventario=inventario, secciones=secciones
    )


@bp.route("/guardar_firma/<int:id>", methods=["POST"], endpoint="guardar_firma")
@login_required
def guardar_firma(id):
    require_edit_permission()
    inventario = get_inventario_for_current_company_or_404(id)
    nombre = request.form.get("nombre", "").strip()
    cedula = request.form.get("cedula", "").strip() or None
    celular = request.form.get("celular", "").strip() or None
    correo = request.form.get("correo", "").strip() or None
    imagen = request.form.get("firma", "").strip()

    if not nombre or not imagen or "," not in imagen:
        flash("Firma invalida.", "error")
        return redirect(url_for("inventarios.ver_inventario", id=id))

    if correo and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
        flash("Correo invalido.", "error")
        return redirect(url_for("inventarios.ver_inventario", id=id))

    encabezado, datos_base64 = imagen.split(",", 1)
    encabezado = encabezado.lower()
    if not encabezado.startswith("data:image/") or ";base64" not in encabezado:
        flash("Firma invalida.", "error")
        return redirect(url_for("inventarios.ver_inventario", id=id))

    try:
        base64.b64decode(datos_base64, validate=True)
    except (ValueError, binascii.Error):
        flash("Firma invalida.", "error")
        return redirect(url_for("inventarios.ver_inventario", id=id))

    db.session.add(
        Firma(
            inventario_id=inventario.id,
            nombre=nombre,
            cedula=cedula,
            celular=celular,
            correo=correo,
            imagen=imagen,
        )
    )
    db.session.commit()
    flash("Firma guardada.", "success")
    return redirect(url_for("inventarios.ver_inventario", id=id))


@bp.route("/inventario_pdf/<int:id>", endpoint="inventario_pdf")
@login_required
def inventario_pdf(id):
    inventario = get_inventario_for_current_company_or_404(id)
    secciones = (
        Seccion.query.filter_by(inventario_id=id).order_by(Seccion.id.asc()).all()
    )
    secciones = [
        seccion
        for seccion in secciones
        if seccion.fotos or seccion.observaciones or (seccion.descripcion or "").strip()
    ]
    firmas = Firma.query.filter_by(inventario_id=id).order_by(Firma.id.asc()).all()
    try:
        nombre_pdf = build_inventory_pdf(inventario, secciones, firmas)
    except Exception:
        current_app.logger.exception("pdf_generation_failed inventario_id=%s", id)
        flash("No se pudo generar el PDF en este momento.", "error")
        return redirect(url_for("inventarios.ver_inventario", id=id))

    current_app.logger.info("pdf_generated inventario_id=%s archivo=%s", id, nombre_pdf)
    return redirect(get_pdf_file_url(inventario.id))
