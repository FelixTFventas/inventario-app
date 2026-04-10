from inventario_app.extensions import db
from inventario_app.models import Inmueble, Inventario, Seccion


def test_admin_can_create_inmueble(client, login, seeded_data, app):
    login(seeded_data["admin_a"].email)

    response = client.post(
        "/crear",
        data={
            "direccion": "Carrera 123",
            "propietario": "Maria",
            "fecha": "2026-04-10",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        inmueble = Inmueble.query.filter_by(direccion="Carrera 123").first()
        assert inmueble is not None
        assert inmueble.empresa_id == seeded_data["empresa_a"].id


def test_admin_can_create_inventory_with_default_sections(
    client, login, seeded_data, app
):
    login(seeded_data["admin_a"].email)

    response = client.post(
        f"/crear_inventario/{seeded_data['inmueble_a'].id}",
        data={"nombre": "Entrega abril", "fecha": "2026-04-11"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        inventario = Inventario.query.filter_by(nombre="Entrega abril").first()
        assert inventario is not None
        assert Seccion.query.filter_by(inventario_id=inventario.id).count() == 6


def test_admin_can_edit_section_name(client, login, seeded_data, app):
    login(seeded_data["admin_a"].email)

    response = client.post(
        f"/editar_seccion/{seeded_data['seccion_a'].id}",
        data={"nombre": "Sala remodelada"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        seccion = db.session.get(Seccion, seeded_data["seccion_a"].id)
        assert seccion.nombre == "Sala remodelada"


def test_admin_can_create_manual_section(client, login, seeded_data, app):
    login(seeded_data["admin_a"].email)

    response = client.post(
        f"/crear_seccion/{seeded_data['inventario_a'].id}",
        data={"nombre": "Balcon"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        assert (
            Seccion.query.filter_by(
                inventario_id=seeded_data["inventario_a"].id,
                nombre="Balcon",
            ).count()
            == 1
        )


def test_viewer_can_open_inventory_without_signature_canvas(client, login, seeded_data):
    login(seeded_data["viewer_a"].email)

    response = client.get(f"/inventario/{seeded_data['inventario_a'].id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="canvas"' not in body
    assert "if (canvas)" in body
