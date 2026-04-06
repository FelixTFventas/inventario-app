from flask_login import UserMixin
from sqlalchemy.sql import func

from ..constants import ROLE_ADMIN
from ..extensions import db


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(30), nullable=False, default=ROLE_ADMIN, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    empresa_id = db.Column(
        db.Integer, db.ForeignKey("empresa.id"), nullable=False, index=True
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
