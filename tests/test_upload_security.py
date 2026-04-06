from io import BytesIO
from pathlib import Path

from inventario_app.models import Foto


def test_upload_rejects_mismatched_image_mimetype(client, login, seeded_data, app):
    login(seeded_data["editor_a"].email)

    response = client.post(
        f"/subir_foto/{seeded_data['seccion_a'].id}",
        data={"fotos": (BytesIO(b"fake image content"), "evidencia.jpg", "text/plain")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "formato de imagen valido" in body
    assert "No se pudo subir ningun archivo valido." in body

    with app.app_context():
        assert Foto.query.filter_by(seccion_id=seeded_data["seccion_a"].id).count() == 0


def test_upload_accepts_valid_image_file(client, login, seeded_data, app):
    login(seeded_data["editor_a"].email)

    response = client.post(
        f"/subir_foto/{seeded_data['seccion_a'].id}",
        data={"fotos": (BytesIO(b"fake png content"), "evidencia.png", "image/png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Se subieron 1 archivo(s)." in response.get_data(as_text=True)

    with app.app_context():
        assert Foto.query.filter_by(seccion_id=seeded_data["seccion_a"].id).count() == 1


def test_uploaded_media_is_served_from_media_route(client, login, seeded_data, app):
    login(seeded_data["editor_a"].email)

    client.post(
        f"/subir_foto/{seeded_data['seccion_a'].id}",
        data={"fotos": (BytesIO(b"fake png content"), "evidencia.png", "image/png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with app.app_context():
        foto = Foto.query.filter_by(seccion_id=seeded_data["seccion_a"].id).first()
        assert foto is not None
        response = client.get(f"/media/uploads/{foto.archivo}")

    assert response.status_code == 200
    assert response.data == b"fake png content"


def test_generated_pdf_route_requires_login(client, login, seeded_data, app):
    pdf_filename = "inventario_test.pdf"
    pdf_path = Path(app.config["PDF_FOLDER"]) / pdf_filename
    pdf_path.write_bytes(b"%PDF-1.4\nmock pdf")

    anonymous_response = client.get(
        f"/media/pdfs/{pdf_filename}", follow_redirects=False
    )
    assert anonymous_response.status_code == 302
    assert (
        "/login?next=%2Fmedia%2Fpdfs%2Finventario_test.pdf"
        in anonymous_response.headers["Location"]
    )

    login(seeded_data["admin_a"].email)
    authenticated_response = client.get(f"/media/pdfs/{pdf_filename}")

    assert authenticated_response.status_code == 200
    assert authenticated_response.data == b"%PDF-1.4\nmock pdf"
