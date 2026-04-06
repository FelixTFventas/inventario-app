def test_login_success_redirects_to_dashboard(client, login, seeded_data):
    response = login(seeded_data["admin_a"].email)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_rejects_invalid_credentials(client, login, seeded_data):
    response = login(
        seeded_data["admin_a"].email, password="bad-pass", follow_redirects=True
    )

    assert response.status_code == 200
    assert "Credenciales invalidas." in response.get_data(as_text=True)


def test_login_rejects_inactive_user(client, login, seeded_data):
    response = login(seeded_data["inactive_a"].email, follow_redirects=True)

    assert response.status_code == 200
    assert "Esta cuenta esta desactivada." in response.get_data(as_text=True)


def test_protected_route_redirects_anonymous_to_login(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert "/login?next=%2F" in response.headers["Location"]


def test_logout_clears_session(client, login, seeded_data):
    login(seeded_data["admin_a"].email)
    response = client.post("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert "Sesion cerrada." in response.get_data(as_text=True)


def test_logout_rejects_get_requests(client, login, seeded_data):
    login(seeded_data["admin_a"].email)

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 405


def test_login_ignores_external_next_redirect(client, login, seeded_data):
    response = login(
        seeded_data["admin_a"].email,
        next_url="https://evil.example/phishing",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_keeps_internal_next_redirect(client, login, seeded_data):
    response = login(
        seeded_data["admin_a"].email,
        next_url="/usuarios",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/usuarios")
