from unittest.mock import patch

from inventario_app.models import Inmueble, Seccion


def test_dashboard_paginates_large_property_list(
    client, login, seeded_data, make_inmueble
):
    for index in range(15):
        make_inmueble(seeded_data["empresa_a"].id, direccion=f"Extra {index}")

    login(seeded_data["admin_a"].email)
    response = client.get("/?page=2")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "P\u00e1gina 2 de 2" in body or "Página 2 de 2" in body


def test_public_view_paginates_sections(client, seeded_data, make_seccion):
    for index in range(12):
        make_seccion(seeded_data["inventario_a"].id, nombre=f"Extra {index}")

    response = client.get(f"/publico/{seeded_data['inventario_a'].token}?page=2")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "P\u00e1gina 2 de 2" in body or "Página 2 de 2" in body


def test_pdf_generation_failure_returns_message(client, login, seeded_data):
    login(seeded_data["admin_a"].email)

    with patch(
        "inventario_app.blueprints.inventarios.build_inventory_pdf",
        side_effect=RuntimeError("boom"),
    ):
        response = client.get(
            f"/inventario_pdf/{seeded_data['inventario_a'].id}", follow_redirects=True
        )

    assert response.status_code == 200
    assert "No se pudo generar el PDF en este momento." in response.get_data(
        as_text=True
    )
