from dataclasses import dataclass

from werkzeug.security import generate_password_hash

from ..constants import ROLE_EDITOR, ROLE_VIEWER
from ..extensions import db
from ..models import Usuario


@dataclass
class ServiceResult:
    is_valid: bool
    error_message: str | None = None


def list_company_users(company_id: int) -> list[Usuario]:
    return (
        Usuario.query.filter_by(empresa_id=company_id).order_by(Usuario.id.asc()).all()
    )


def create_employee(
    company_id: int,
    nombre: str,
    email: str,
    password_raw: str,
    rol: str,
) -> ServiceResult:
    nombre = nombre.strip()
    email = email.strip().lower()
    rol = rol.strip()

    if rol not in {ROLE_EDITOR, ROLE_VIEWER}:
        return ServiceResult(False, "Selecciona un rol valido para el empleado.")

    if not nombre or not email or not password_raw:
        return ServiceResult(False, "Nombre, correo y contrasena son obligatorios.")

    existe = Usuario.query.filter_by(email=email).first()
    if existe:
        return ServiceResult(False, "Ese correo ya esta registrado.")

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
    return ServiceResult(True)


def change_user_role(
    usuario: Usuario, current_user_id: int, nuevo_rol: str
) -> ServiceResult:
    nuevo_rol = nuevo_rol.strip()

    if usuario.id == current_user_id:
        return ServiceResult(False, "No puedes cambiar tu propio rol desde este panel.")

    if usuario.rol == "admin_empresa":
        return ServiceResult(
            False, "El rol del administrador principal no se cambia desde aqui."
        )

    if nuevo_rol not in {ROLE_EDITOR, ROLE_VIEWER}:
        return ServiceResult(False, "Selecciona un rol valido.")

    usuario.rol = nuevo_rol
    db.session.commit()
    return ServiceResult(True)


def toggle_user_status(usuario: Usuario, current_user_id: int) -> ServiceResult:
    if usuario.id == current_user_id:
        return ServiceResult(
            False, "No puedes desactivar tu propia cuenta desde este panel."
        )

    if usuario.rol == "admin_empresa":
        return ServiceResult(
            False, "La cuenta principal no se activa ni desactiva desde aqui."
        )

    usuario.activo = not usuario.activo
    db.session.commit()
    return ServiceResult(True)


def reset_user_password(usuario: Usuario, nueva_password: str) -> ServiceResult:
    if usuario.rol == "admin_empresa":
        return ServiceResult(
            False, "La cuenta principal no cambia su contrasena desde este panel."
        )

    if len(nueva_password) < 6:
        return ServiceResult(
            False, "La nueva contrasena debe tener al menos 6 caracteres."
        )

    usuario.password = generate_password_hash(nueva_password)
    db.session.commit()
    return ServiceResult(True)
