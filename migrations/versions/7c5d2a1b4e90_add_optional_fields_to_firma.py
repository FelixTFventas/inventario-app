"""add optional fields to firma

Revision ID: 7c5d2a1b4e90
Revises: 2e4f6a8b9c10
Create Date: 2026-04-15 09:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c5d2a1b4e90"
down_revision = "2e4f6a8b9c10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("firma", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cedula", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("celular", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("correo", sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table("firma", schema=None) as batch_op:
        batch_op.drop_column("correo")
        batch_op.drop_column("celular")
        batch_op.drop_column("cedula")
