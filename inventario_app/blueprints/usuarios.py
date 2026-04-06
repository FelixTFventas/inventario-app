from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from ..constants import ROLE_ADMIN, ROLE_EDITOR, ROLE_VIEWER
from ..extensions import db
from ..models import Usuario
from ..services.access import (
    company_required,
    get_effective_company_id,
    get_user_for_current_company_or_404,
    require_admin_permission,
)


bp = Blueprint("usuarios", __name__)


@bp.route("/usuarios", methods=["GET", "POST"], endpoint="usuarios")
@login_required
def usuarios():
    company_required()
    require_admin_permission()
    company_id = get_effective_company_id()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password_raw = request.form.get("password", "")
        rol = request.form.get("rol", ROLE_VIEWER).strip()

        if rol not in {ROLE_EDITOR, ROLE_VIEWER}:
            flash("Selecciona un rol valido para el empleado.", "error")
            return redirect(url_for("usuarios.usuarios"))

        if not nombre or not email or not password_raw:
            flash("Nombre, correo y contrasena son obligatorios.", "error")
            return redirect(url_for("usuarios.usuarios"))

        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            flash("Ese correo ya esta registrado.", "error")
            return redirect(url_for("usuarios.usuarios"))

        nuevo = Usuario(
            nombre=nombre,
            email=email,
            password=generate_password_hash(password_raw),
            empresa_id=company_id,
            rol=rol,
            activo=True,
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Empleado creado correctamente.", "success")
        return redirect(url_for("usuarios.usuarios"))

    empleados = (
        Usuario.query.filter_by(empresa_id=company_id).order_by(Usuario.id.asc()).all()
    )
    return render_template("usuarios.html", empleados=empleados)


@bp.route("/usuarios/<int:id>/rol", methods=["POST"], endpoint="actualizar_rol_usuario")
@login_required
def actualizar_rol_usuario(id):
    company_required()
    require_admin_permission()

    usuario = get_user_for_current_company_or_404(id)
    nuevo_rol = request.form.get("rol", "").strip()

    if usuario.id == current_user.id:
        flash("No puedes cambiar tu propio rol desde este panel.", "error")
        return redirect(url_for("usuarios.usuarios"))

    if usuario.rol == ROLE_ADMIN:
        flash("El rol del administrador principal no se cambia desde aqui.", "error")
        return redirect(url_for("usuarios.usuarios"))

    if nuevo_rol not in {ROLE_EDITOR, ROLE_VIEWER}:
        flash("Selecciona un rol valido.", "error")
        return redirect(url_for("usuarios.usuarios"))

    usuario.rol = nuevo_rol
    db.session.commit()
    flash("Rol actualizado correctamente.", "success")
    return redirect(url_for("usuarios.usuarios"))


@bp.route(
    "/usuarios/<int:id>/estado", methods=["POST"], endpoint="actualizar_estado_usuario"
)
@login_required
def actualizar_estado_usuario(id):
    company_required()
    require_admin_permission()

    usuario = get_user_for_current_company_or_404(id)

    if usuario.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta desde este panel.", "error")
        return redirect(url_for("usuarios.usuarios"))

    if usuario.rol == ROLE_ADMIN:
        flash("La cuenta principal no se activa ni desactiva desde aqui.", "error")
        return redirect(url_for("usuarios.usuarios"))

    usuario.activo = not usuario.activo
    db.session.commit()
    flash(
        "Usuario activado correctamente."
        if usuario.activo
        else "Usuario desactivado correctamente.",
        "success",
    )
    return redirect(url_for("usuarios.usuarios"))


@bp.route(
    "/usuarios/<int:id>/password",
    methods=["POST"],
    endpoint="actualizar_password_usuario",
)
@login_required
def actualizar_password_usuario(id):
    company_required()
    require_admin_permission()

    usuario = get_user_for_current_company_or_404(id)
    nueva_password = request.form.get("password", "")

    if usuario.rol == ROLE_ADMIN:
        flash("La cuenta principal no cambia su contrasena desde este panel.", "error")
        return redirect(url_for("usuarios.usuarios"))

    if len(nueva_password) < 6:
        flash("La nueva contrasena debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("usuarios.usuarios"))

    usuario.password = generate_password_hash(nueva_password)
    db.session.commit()
    flash("Contrasena restablecida correctamente.", "success")
    return redirect(url_for("usuarios.usuarios"))
