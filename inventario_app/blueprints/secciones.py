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
from ..models import Foto, Observacion, Seccion
from ..services.access import (
    get_foto_for_current_company_or_404,
    get_inventario_for_current_company_or_404,
    get_seccion_for_current_company_or_404,
    require_edit_permission,
)
from ..services.media_service import (
    delete_uploaded_file,
    get_uploaded_file_url,
    save_uploaded_file,
)
from ..utils.files import validate_uploaded_file
from ..utils.files import is_video_filename


bp = Blueprint("secciones", __name__)


@bp.route("/seccion/<int:id>", endpoint="ver_seccion")
@login_required
def ver_seccion(id):
    seccion = get_seccion_for_current_company_or_404(id)
    fotos = Foto.query.filter_by(seccion_id=id).order_by(Foto.id.desc()).all()
    observaciones = (
        Observacion.query.filter_by(seccion_id=id).order_by(Observacion.id.desc()).all()
    )
    return render_template(
        "seccion.html",
        seccion=seccion,
        fotos=fotos,
        observaciones=observaciones,
        inventario_id=seccion.inventario_id,
        uploaded_file_url=get_uploaded_file_url,
        is_video_file=is_video_filename,
    )


@bp.route("/subir_foto/<int:id>", methods=["POST"], endpoint="subir_foto")
@login_required
def subir_foto(id):
    require_edit_permission()
    seccion = get_seccion_for_current_company_or_404(id)
    archivos = request.files.getlist("fotos")
    guardados = 0

    for archivo in archivos:
        if not archivo or not archivo.filename:
            continue
        validation_error = validate_uploaded_file(archivo)
        if validation_error:
            current_app.logger.warning(
                "upload_rejected seccion_id=%s filename=%s reason=%s",
                seccion.id,
                archivo.filename,
                validation_error,
            )
            flash(validation_error, "error")
            continue

        try:
            nombre_archivo = save_uploaded_file(archivo)
        except Exception:
            current_app.logger.exception(
                "upload_failed seccion_id=%s filename=%s", seccion.id, archivo.filename
            )
            flash(f"No se pudo guardar el archivo: {archivo.filename}", "error")
            continue

        db.session.add(Foto(seccion_id=seccion.id, archivo=nombre_archivo))
        guardados += 1

    if guardados:
        db.session.commit()
        current_app.logger.info(
            "upload_saved seccion_id=%s cantidad=%s", seccion.id, guardados
        )
        flash(f"Se subieron {guardados} archivo(s).", "success")
    else:
        db.session.rollback()
        flash("No se pudo subir ningun archivo valido.", "error")

    return redirect(url_for("secciones.ver_seccion", id=id))


@bp.route("/eliminar_foto/<int:id>", methods=["POST"], endpoint="eliminar_foto")
@login_required
def eliminar_foto(id):
    require_edit_permission()
    foto = get_foto_for_current_company_or_404(id)
    seccion_id = foto.seccion_id
    db.session.delete(foto)
    db.session.commit()
    delete_uploaded_file(foto.archivo)
    current_app.logger.info("upload_deleted foto_id=%s seccion_id=%s", id, seccion_id)
    flash("Archivo eliminado.", "success")
    return redirect(url_for("secciones.ver_seccion", id=seccion_id))


@bp.route("/crear_observacion/<int:id>", methods=["POST"], endpoint="crear_observacion")
@login_required
def crear_observacion(id):
    require_edit_permission()
    seccion = get_seccion_for_current_company_or_404(id)
    comentario = request.form.get("comentario", "").strip()

    if not comentario:
        flash("La observacion no puede estar vacia.", "error")
        return redirect(url_for("secciones.ver_seccion", id=id))

    db.session.add(Observacion(seccion_id=seccion.id, comentario=comentario))
    db.session.commit()
    current_app.logger.info("observacion_created seccion_id=%s", seccion.id)
    flash("Observacion guardada.", "success")
    return redirect(url_for("secciones.ver_seccion", id=id))


@bp.route("/crear_seccion/<int:id>", methods=["POST"], endpoint="crear_seccion")
@login_required
def crear_seccion(id):
    require_edit_permission()
    inventario = get_inventario_for_current_company_or_404(id)
    nombre = request.form.get("nombre", "").strip()

    if not nombre:
        flash("Debes indicar el nombre de la seccion.", "error")
        return redirect(url_for("inventarios.ver_inventario", id=id))

    db.session.add(Seccion(inventario_id=inventario.id, nombre=nombre))
    db.session.commit()
    flash("Seccion creada correctamente.", "success")
    return redirect(url_for("inventarios.ver_inventario", id=id))


@bp.route("/eliminar_seccion/<int:id>", methods=["POST"], endpoint="eliminar_seccion")
@login_required
def eliminar_seccion(id):
    require_edit_permission()
    seccion = get_seccion_for_current_company_or_404(id)
    inventario_id = seccion.inventario_id
    db.session.delete(seccion)
    db.session.commit()
    flash("Seccion eliminada.", "success")
    return redirect(url_for("inventarios.ver_inventario", id=inventario_id))


@bp.route(
    "/editar_seccion/<int:id>", methods=["GET", "POST"], endpoint="editar_seccion"
)
@login_required
def editar_seccion(id):
    seccion = get_seccion_for_current_company_or_404(id)

    if request.method == "POST":
        require_edit_permission()
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre no puede estar vacio.", "error")
            return redirect(url_for("secciones.editar_seccion", id=id))

        seccion.nombre = nombre
        db.session.commit()
        flash("Seccion actualizada.", "success")
        return redirect(url_for("inventarios.ver_inventario", id=seccion.inventario_id))

    return render_template("editar_seccion.html", seccion=seccion)
