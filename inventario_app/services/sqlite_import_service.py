from datetime import date, datetime
import sqlite3
from pathlib import Path

from sqlalchemy import text

from ..extensions import db
from ..models import (
    Empresa,
    Firma,
    Foto,
    Inmueble,
    Inventario,
    Observacion,
    Seccion,
    Usuario,
)
from .bootstrap_service import seed_initial_data


IMPORT_ORDER = [
    ("empresa", Empresa),
    ("usuario", Usuario),
    ("inmueble", Inmueble),
    ("inventario", Inventario),
    ("seccion", Seccion),
    ("foto", Foto),
    ("observacion", Observacion),
    ("firma", Firma),
]


def import_from_sqlite(source_path: str, reset_target: bool = False) -> dict[str, int]:
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"No existe la base SQLite origen: {source}")

    inspector = db.inspect(db.engine)
    tablas = set(inspector.get_table_names())
    expected_tables = {table_name for table_name, _ in IMPORT_ORDER}
    missing_tables = expected_tables - tablas
    if missing_tables:
        faltantes = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            f"La base destino no tiene el esquema completo. Ejecuta 'flask db upgrade' primero. Faltan: {faltantes}"
        )

    if reset_target:
        _clear_target_tables()
    elif _target_has_data():
        raise RuntimeError(
            "La base destino ya tiene datos. Usa --reset-target para limpiarla antes de importar."
        )

    imported_counts: dict[str, int] = {}
    with sqlite3.connect(source) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        for table_name, model in IMPORT_ORDER:
            rows = [
                dict(row)
                for row in cursor.execute(f"SELECT * FROM {table_name} ORDER BY id")
            ]
            rows = [_normalize_import_row(table_name, row) for row in rows]
            if rows:
                db.session.execute(model.__table__.insert(), rows)
            imported_counts[table_name] = len(rows)

    db.session.commit()
    _sync_sequences_if_needed()
    seed_initial_data()
    return imported_counts


def _target_has_data() -> bool:
    for _, model in IMPORT_ORDER:
        if db.session.query(model.id).first() is not None:
            return True
    return False


def _clear_target_tables() -> None:
    for _, model in reversed(IMPORT_ORDER):
        db.session.execute(model.__table__.delete())
    db.session.commit()


def _sync_sequences_if_needed() -> None:
    if db.engine.dialect.name != "postgresql":
        return

    for table_name, _ in IMPORT_ORDER:
        db.session.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)"
            )
        )
    db.session.commit()


def _normalize_import_row(table_name: str, row: dict) -> dict:
    now = datetime.utcnow()
    normalized = dict(row)

    if table_name == "inmueble" and isinstance(normalized.get("fecha_recepcion"), str):
        normalized["fecha_recepcion"] = date.fromisoformat(
            normalized["fecha_recepcion"].strip()
        )
    if table_name == "inventario" and isinstance(normalized.get("fecha"), str):
        normalized["fecha"] = date.fromisoformat(normalized["fecha"].strip())

    for field_name in ("created_at", "updated_at"):
        field_value = normalized.get(field_name)
        if isinstance(field_value, str):
            normalized[field_name] = datetime.fromisoformat(field_value.strip())

    normalized.setdefault("created_at", now)
    normalized.setdefault("updated_at", now)
    return normalized
