import sys
from datetime import date
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inventario_app import create_app
from inventario_app.constants import ROLE_ADMIN, ROLE_EDITOR, ROLE_VIEWER, STATUS_ACTIVE
from inventario_app.extensions import db
from inventario_app.models import Empresa, Inmueble, Inventario, Seccion, Usuario


@pytest.fixture()
def app(tmp_path):
    database_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    pdf_dir = tmp_path / "pdfs"
    upload_dir.mkdir()
    pdf_dir.mkdir()

    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SKIP_DATA_SEED": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "UPLOAD_FOLDER": str(upload_dir),
            "PDF_FOLDER": str(pdf_dir),
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_company(app):
    def factory(
        nombre: str, slug: str, estado: str = STATUS_ACTIVE, activo: bool = True
    ):
        empresa = Empresa(nombre=nombre, slug=slug, estado=estado, activo=activo)
        db.session.add(empresa)
        db.session.commit()
        return empresa

    return factory


@pytest.fixture()
def make_user(app):
    def factory(
        empresa_id: int,
        nombre: str,
        email: str,
        password: str = "secret123",
        rol: str = ROLE_ADMIN,
        activo: bool = True,
    ):
        usuario = Usuario(
            nombre=nombre,
            email=email,
            password=generate_password_hash(password),
            empresa_id=empresa_id,
            rol=rol,
            activo=activo,
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario

    return factory


@pytest.fixture()
def make_inmueble(app):
    def factory(
        empresa_id: int, direccion: str = "Calle 1", propietario: str = "Owner"
    ):
        inmueble = Inmueble(
            direccion=direccion,
            propietario=propietario,
            fecha_recepcion=date(2026, 4, 1),
            empresa_id=empresa_id,
        )
        db.session.add(inmueble)
        db.session.commit()
        return inmueble

    return factory


@pytest.fixture()
def make_inventario(app):
    def factory(
        inmueble_id: int, nombre: str = "Entrega inicial", token: str = "public-token"
    ):
        inventario = Inventario(
            inmueble_id=inmueble_id,
            nombre=nombre,
            fecha=date(2026, 4, 2),
            token=token,
        )
        db.session.add(inventario)
        db.session.commit()
        return inventario

    return factory


@pytest.fixture()
def make_seccion(app):
    def factory(inventario_id: int, nombre: str = "Sala"):
        seccion = Seccion(inventario_id=inventario_id, nombre=nombre)
        db.session.add(seccion)
        db.session.commit()
        return seccion

    return factory


@pytest.fixture()
def seeded_data(
    app, make_company, make_user, make_inmueble, make_inventario, make_seccion
):
    empresa_a = make_company("Empresa A", "empresa-a")
    empresa_b = make_company("Empresa B", "empresa-b")

    admin_a = make_user(empresa_a.id, "Admin A", "admin-a@test.com", rol=ROLE_ADMIN)
    editor_a = make_user(empresa_a.id, "Editor A", "editor-a@test.com", rol=ROLE_EDITOR)
    viewer_a = make_user(empresa_a.id, "Viewer A", "viewer-a@test.com", rol=ROLE_VIEWER)
    admin_b = make_user(empresa_b.id, "Admin B", "admin-b@test.com", rol=ROLE_ADMIN)
    inactive_a = make_user(
        empresa_a.id,
        "Inactive A",
        "inactive-a@test.com",
        rol=ROLE_VIEWER,
        activo=False,
    )

    inmueble_a = make_inmueble(empresa_a.id, direccion="Calle A")
    inmueble_b = make_inmueble(empresa_b.id, direccion="Calle B")
    inventario_a = make_inventario(inmueble_a.id, token="token-a")
    inventario_b = make_inventario(inmueble_b.id, token="token-b")
    seccion_a = make_seccion(inventario_a.id, nombre="Sala A")

    return {
        "empresa_a": empresa_a,
        "empresa_b": empresa_b,
        "admin_a": admin_a,
        "editor_a": editor_a,
        "viewer_a": viewer_a,
        "admin_b": admin_b,
        "inactive_a": inactive_a,
        "inmueble_a": inmueble_a,
        "inmueble_b": inmueble_b,
        "inventario_a": inventario_a,
        "inventario_b": inventario_b,
        "seccion_a": seccion_a,
    }


@pytest.fixture()
def login(client):
    def do_login(
        email: str,
        password: str = "secret123",
        follow_redirects: bool = False,
        next_url: str | None = None,
    ):
        login_url = "/login"
        if next_url:
            login_url = f"{login_url}?next={next_url}"
        return client.post(
            login_url,
            data={"email": email, "password": password},
            follow_redirects=follow_redirects,
        )

    return do_login
