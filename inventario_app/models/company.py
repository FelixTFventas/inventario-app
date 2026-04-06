from sqlalchemy.sql import func

from ..constants import STATUS_ACTIVE
from ..extensions import db


class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    estado = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    usuarios = db.relationship(
        "Usuario",
        backref="empresa",
        lazy=True,
        cascade="all, delete-orphan",
    )
    inmuebles = db.relationship(
        "Inmueble",
        backref="empresa",
        lazy=True,
        cascade="all, delete-orphan",
    )
