import os

from werkzeug.security import generate_password_hash

from ..constants import (
    DEFAULT_SUPERADMIN_EMAIL,
    DEFAULT_SUPERADMIN_NAME,
    DEFAULT_SUPERADMIN_PASSWORD,
    INTERNAL_COMPANY_SLUG,
    ROLE_SUPERADMIN,
    STATUS_ACTIVE,
)
from ..config import IS_PRODUCTION
from ..extensions import db
from ..models import Empresa, Usuario


def get_superadmin_seed_credentials() -> tuple[str, str, str]:
    email = os.environ.get("SUPERADMIN_EMAIL")
    password = os.environ.get("SUPERADMIN_PASSWORD")
    superadmin_name = os.environ.get("SUPERADMIN_NAME", DEFAULT_SUPERADMIN_NAME)

    if IS_PRODUCTION and (not email or not password):
        raise RuntimeError(
            "Configura SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD antes de iniciar en produccion."
        )

    return (
        superadmin_name,
        email or DEFAULT_SUPERADMIN_EMAIL,
        password or DEFAULT_SUPERADMIN_PASSWORD,
    )


def seed_initial_data() -> None:
    inspector = db.inspect(db.engine)
    tablas = set(inspector.get_table_names())
    if not {"empresa", "usuario"}.issubset(tablas):
        return

    superadmin = Usuario.query.filter_by(rol=ROLE_SUPERADMIN).first()
    if not superadmin:
        superadmin_name, superadmin_email, superadmin_password = (
            get_superadmin_seed_credentials()
        )
        empresa_dummy = Empresa.query.filter_by(slug=INTERNAL_COMPANY_SLUG).first()
        if not empresa_dummy:
            empresa_dummy = Empresa(
                nombre="Plataforma Interna",
                slug=INTERNAL_COMPANY_SLUG,
                estado=STATUS_ACTIVE,
                activo=True,
            )
            db.session.add(empresa_dummy)
            db.session.flush()

        superadmin = Usuario(
            nombre=superadmin_name,
            email=superadmin_email,
            password=generate_password_hash(superadmin_password),
            rol=ROLE_SUPERADMIN,
            activo=True,
            empresa_id=empresa_dummy.id,
        )
        db.session.add(superadmin)
        db.session.commit()
