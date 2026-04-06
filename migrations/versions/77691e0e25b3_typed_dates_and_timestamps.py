"""typed dates and timestamps

Revision ID: 77691e0e25b3
Revises: 6923b6fd053b
Create Date: 2026-04-06 09:20:17.193211

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "77691e0e25b3"
down_revision = "6923b6fd053b"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table("empresa", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.create_index(batch_op.f("ix_empresa_estado"), ["estado"], unique=False)

    with op.batch_alter_table("firma", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_firma_inventario_id"), ["inventario_id"], unique=False
        )

    with op.batch_alter_table("foto", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_foto_seccion_id"), ["seccion_id"], unique=False
        )

    with op.batch_alter_table("inmueble", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("fecha_recepcion_date", sa.Date(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_inmueble_empresa_id"), ["empresa_id"], unique=False
        )

    if dialect == "postgresql":
        op.execute(
            "UPDATE inmueble SET fecha_recepcion_date = CAST(fecha_recepcion AS DATE)"
        )
    else:
        op.execute("UPDATE inmueble SET fecha_recepcion_date = fecha_recepcion")

    with op.batch_alter_table("inmueble", schema=None) as batch_op:
        batch_op.drop_column("fecha_recepcion")
        batch_op.alter_column(
            "fecha_recepcion_date",
            new_column_name="fecha_recepcion",
            existing_type=sa.Date(),
            nullable=False,
        )

    with op.batch_alter_table("inventario", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("fecha_date", sa.Date(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_inventario_inmueble_id"), ["inmueble_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_inventario_token"), ["token"], unique=True)

    if dialect == "postgresql":
        op.execute("UPDATE inventario SET fecha_date = CAST(fecha AS DATE)")
    else:
        op.execute("UPDATE inventario SET fecha_date = fecha")

    with op.batch_alter_table("inventario", schema=None) as batch_op:
        batch_op.drop_column("fecha")
        batch_op.alter_column(
            "fecha_date",
            new_column_name="fecha",
            existing_type=sa.Date(),
            nullable=False,
        )

    with op.batch_alter_table("observacion", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_observacion_seccion_id"), ["seccion_id"], unique=False
        )

    with op.batch_alter_table("seccion", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_seccion_inventario_id"), ["inventario_id"], unique=False
        )

    with op.batch_alter_table("usuario", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_usuario_empresa_id"), ["empresa_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_usuario_rol"), ["rol"], unique=False)


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table("usuario", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_usuario_rol"))
        batch_op.drop_index(batch_op.f("ix_usuario_empresa_id"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    with op.batch_alter_table("seccion", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_seccion_inventario_id"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    with op.batch_alter_table("observacion", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_observacion_seccion_id"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    with op.batch_alter_table("inventario", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_inventario_token"))
        batch_op.drop_index(batch_op.f("ix_inventario_inmueble_id"))
        batch_op.add_column(
            sa.Column("fecha_text", sa.VARCHAR(length=50), nullable=True)
        )
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    if dialect == "postgresql":
        op.execute("UPDATE inventario SET fecha_text = TO_CHAR(fecha, 'YYYY-MM-DD')")
    else:
        op.execute("UPDATE inventario SET fecha_text = CAST(fecha AS TEXT)")

    with op.batch_alter_table("inventario", schema=None) as batch_op:
        batch_op.drop_column("fecha")
        batch_op.alter_column(
            "fecha_text",
            new_column_name="fecha",
            existing_type=sa.VARCHAR(length=50),
            nullable=False,
        )

    with op.batch_alter_table("inmueble", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_inmueble_empresa_id"))
        batch_op.add_column(
            sa.Column("fecha_recepcion_text", sa.VARCHAR(length=50), nullable=True)
        )
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    if dialect == "postgresql":
        op.execute(
            "UPDATE inmueble SET fecha_recepcion_text = TO_CHAR(fecha_recepcion, 'YYYY-MM-DD')"
        )
    else:
        op.execute(
            "UPDATE inmueble SET fecha_recepcion_text = CAST(fecha_recepcion AS TEXT)"
        )

    with op.batch_alter_table("inmueble", schema=None) as batch_op:
        batch_op.drop_column("fecha_recepcion")
        batch_op.alter_column(
            "fecha_recepcion_text",
            new_column_name="fecha_recepcion",
            existing_type=sa.VARCHAR(length=50),
            nullable=False,
        )

    with op.batch_alter_table("foto", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_foto_seccion_id"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    with op.batch_alter_table("firma", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_firma_inventario_id"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    with op.batch_alter_table("empresa", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_empresa_estado"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
