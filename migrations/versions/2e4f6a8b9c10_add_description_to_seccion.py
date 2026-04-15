"""add description to seccion

Revision ID: 2e4f6a8b9c10
Revises: 77691e0e25b3
Create Date: 2026-04-15 08:55:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2e4f6a8b9c10"
down_revision = "77691e0e25b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("seccion", schema=None) as batch_op:
        batch_op.add_column(sa.Column("descripcion", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("seccion", schema=None) as batch_op:
        batch_op.drop_column("descripcion")
