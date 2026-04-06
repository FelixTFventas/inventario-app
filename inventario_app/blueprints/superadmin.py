from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_required
from werkzeug.security import generate_password_hash

from ..constants import (
    INTERNAL_COMPANY_SLUG,
    ROLE_ADMIN,
    STATUS_ACTIVE,
    STATUS_CANCELLED,
    VALID_COMPANY_STATUSES,
)
from ..extensions import db
from ..models import Empresa, Usuario
from ..services.access import require_superadmin_permission
from ..services.company_service import unique_company_slug


bp = Blueprint("superadmin", __name__)


@bp.route(
    "/superadmin/empresas", methods=["GET", "POST"], endpoint="superadmin_empresas"
)
@login_required
def superadmin_empresas():
    require_superadmin_permission()

    if request.method == "POST":
        empresa_nombre = request.form.get("empresa", "").strip()
        admin_nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password_raw = request.form.get("password", "")
        estado = request.form.get("estado", STATUS_ACTIVE).strip()

        if not empresa_nombre or not admin_nombre or not email or not password_raw:
            flash(
                "Empresa, admin, correo y contrasena temporal son obligatorios.",
                "error",
            )
            return redirect(url_for("superadmin.superadmin_empresas"))

        if estado not in VALID_COMPANY_STATUSES:
            flash("Selecciona un estado valido para la empresa.", "error")
            return redirect(url_for("superadmin.superadmin_empresas"))

        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            flash("Ese correo ya esta registrado.", "error")
            return redirect(url_for("superadmin.superadmin_empresas"))

        empresa = Empresa(
            nombre=empresa_nombre,
            slug=unique_company_slug(empresa_nombre),
            estado=estado,
            activo=True,
        )
        db.session.add(empresa)
        db.session.flush()

        nuevo = Usuario(
            nombre=admin_nombre,
            email=email,
            password=generate_password_hash(password_raw),
            empresa_id=empresa.id,
            rol=ROLE_ADMIN,
            activo=True,
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Empresa creada correctamente con su admin principal.", "success")
        return redirect(url_for("superadmin.superadmin_empresas"))

    empresas = (
        Empresa.query.filter(Empresa.slug != INTERNAL_COMPANY_SLUG)
        .order_by(Empresa.nombre.asc())
        .all()
    )
    return render_template("superadmin_empresas.html", empresas=empresas)


@bp.route(
    "/superadmin/empresas/<int:id>/estado",
    methods=["POST"],
    endpoint="superadmin_actualizar_estado_empresa",
)
@login_required
def superadmin_actualizar_estado_empresa(id):
    require_superadmin_permission()
    empresa = db.session.get(Empresa, id)
    if not empresa:
        abort(404)

    estado = request.form.get("estado", "").strip()
    if estado not in VALID_COMPANY_STATUSES:
        flash("Selecciona un estado valido.", "error")
        return redirect(url_for("superadmin.superadmin_empresas"))

    empresa.estado = estado
    empresa.activo = estado != STATUS_CANCELLED
    db.session.commit()

    if estado != STATUS_ACTIVE and session.get("superadmin_company_id") == empresa.id:
        session.pop("superadmin_company_id", None)

    flash("Estado de la empresa actualizado correctamente.", "success")
    return redirect(url_for("superadmin.superadmin_empresas"))


@bp.route(
    "/superadmin/empresas/<int:id>/entrar",
    methods=["POST"],
    endpoint="superadmin_entrar_empresa",
)
@login_required
def superadmin_entrar_empresa(id):
    require_superadmin_permission()
    empresa = db.session.get(Empresa, id)
    if not empresa:
        abort(404)

    session["superadmin_company_id"] = empresa.id
    flash(f"Modo superadmin activo sobre {empresa.nombre}.", "success")
    return redirect(url_for("dashboard.index"))


@bp.route(
    "/superadmin/salir-empresa",
    methods=["POST"],
    endpoint="superadmin_salir_empresa",
)
@login_required
def superadmin_salir_empresa():
    require_superadmin_permission()
    session.pop("superadmin_company_id", None)
    flash("Saliste del modo empresa.", "success")
    return redirect(url_for("superadmin.superadmin_empresas"))
