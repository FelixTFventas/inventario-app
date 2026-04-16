from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..constants import ROLE_EDITOR, ROLE_VIEWER
from ..services.access import (
    company_required,
    get_effective_company_id,
    get_user_for_current_company_or_404,
    require_admin_permission,
)
from ..services.user_service import (
    change_user_role,
    create_employee,
    list_company_users,
    reset_user_password,
    toggle_user_status,
)


bp = Blueprint("usuarios", __name__)


@bp.route("/usuarios", methods=["GET", "POST"], endpoint="usuarios")
@login_required
def usuarios():
    company_required()
    require_admin_permission()
    company_id = get_effective_company_id()

    if request.method == "POST":
        result = create_employee(
            company_id,
            request.form.get("nombre", ""),
            request.form.get("email", ""),
            request.form.get("password", ""),
            request.form.get("rol", ROLE_VIEWER),
        )
        if not result.is_valid:
            flash(result.error_message, "error")
            return redirect(url_for("usuarios.usuarios"))

        flash("Empleado creado correctamente.", "success")
        return redirect(url_for("usuarios.usuarios"))

    empleados = list_company_users(company_id)
    return render_template("usuarios.html", empleados=empleados)


@bp.route("/usuarios/<int:id>/rol", methods=["POST"], endpoint="actualizar_rol_usuario")
@login_required
def actualizar_rol_usuario(id):
    company_required()
    require_admin_permission()

    usuario = get_user_for_current_company_or_404(id)
    result = change_user_role(usuario, current_user.id, request.form.get("rol", ""))
    if not result.is_valid:
        flash(result.error_message, "error")
        return redirect(url_for("usuarios.usuarios"))

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
    result = toggle_user_status(usuario, current_user.id)
    if not result.is_valid:
        flash(result.error_message, "error")
        return redirect(url_for("usuarios.usuarios"))

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
    result = reset_user_password(usuario, request.form.get("password", ""))
    if not result.is_valid:
        flash(result.error_message, "error")
        return redirect(url_for("usuarios.usuarios"))

    flash("Contrasena restablecida correctamente.", "success")
    return redirect(url_for("usuarios.usuarios"))
