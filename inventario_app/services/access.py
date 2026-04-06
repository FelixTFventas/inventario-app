from flask import abort, session
from flask_login import current_user, logout_user

from ..constants import EDIT_ROLES, ROLE_ADMIN, ROLE_SUPERADMIN, STATUS_ACTIVE
from ..extensions import db
from ..models import Empresa, Foto, Inmueble, Inventario, Seccion, Usuario


def user_can_edit(user) -> bool:
    return bool(user and user.is_authenticated and user.rol in EDIT_ROLES)


def user_is_superadmin(user) -> bool:
    return bool(user and user.is_authenticated and user.rol == ROLE_SUPERADMIN)


def user_is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.rol == ROLE_ADMIN)


def require_edit_permission() -> None:
    if not user_can_edit(current_user):
        abort(403)


def require_admin_permission() -> None:
    if not (user_is_admin(current_user) or user_is_superadmin(current_user)):
        abort(403)


def require_superadmin_permission() -> None:
    if not user_is_superadmin(current_user):
        abort(403)


def get_effective_company() -> Empresa | None:
    if not current_user.is_authenticated:
        return None
    if user_is_superadmin(current_user):
        company_id = session.get("superadmin_company_id")
        if not company_id:
            return None
        return db.session.get(Empresa, company_id)
    return current_user.empresa


def get_effective_company_id() -> int | None:
    empresa = get_effective_company()
    return empresa.id if empresa else None


def company_required() -> None:
    if not current_user.is_authenticated:
        abort(403)
    if user_is_superadmin(current_user):
        empresa = get_effective_company()
        if not empresa:
            abort(403)
        return
    if not getattr(current_user, "activo", True):
        logout_user()
        abort(403)
    if (
        not current_user.empresa
        or not current_user.empresa.activo
        or current_user.empresa.estado != STATUS_ACTIVE
    ):
        logout_user()
        abort(403)


def get_inmueble_for_current_company_or_404(inmueble_id: int) -> Inmueble:
    company_required()
    inmueble = db.session.get(Inmueble, inmueble_id)
    if not inmueble:
        abort(404)
    if inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return inmueble


def get_inventario_for_current_company_or_404(inventario_id: int) -> Inventario:
    company_required()
    inventario = db.session.get(Inventario, inventario_id)
    if not inventario:
        abort(404)
    if inventario.inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return inventario


def get_seccion_for_current_company_or_404(seccion_id: int) -> Seccion:
    company_required()
    seccion = db.session.get(Seccion, seccion_id)
    if not seccion:
        abort(404)
    if seccion.inventario.inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return seccion


def get_foto_for_current_company_or_404(foto_id: int) -> Foto:
    company_required()
    foto = db.session.get(Foto, foto_id)
    if not foto:
        abort(404)
    if foto.seccion.inventario.inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return foto


def get_user_for_current_company_or_404(user_id: int) -> Usuario:
    company_required()
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        abort(404)
    if usuario.empresa_id != get_effective_company_id():
        abort(403)
    return usuario
