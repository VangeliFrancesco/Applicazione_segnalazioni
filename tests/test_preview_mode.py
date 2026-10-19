from app import create_app


def test_preview_mode_is_interactive_without_mysql():
    app = create_app(
        {
            "TESTING": True,
            "PREVIEW_MODE": True,
            "SECRET_KEY": "test-secret",
        }
    )
    client = app.test_client()

    home = client.get("/")
    assert home.status_code == 200
    assert b"Attraversamento pedonale poco illuminato" in home.data
    assert b"demo.utente@example.test" in home.data

    registration = client.post(
        "/register",
        data={
            "first_name": "Nuovo",
            "last_name": "Utente",
            "email": "nuovo@example.test",
            "password": "Password1!",
            "confirm_password": "Password1!",
        },
        follow_redirects=True,
    )
    assert registration.status_code == 200
    assert b"Registrazione completata" in registration.data

    login = client.post(
        "/login",
        data={"email": "demo.utente@example.test", "password": "DemoUtente1!"},
        follow_redirects=True,
    )
    assert login.status_code == 200
    assert b"Dashboard" in login.data
    assert b"Nuova segnalazione" in login.data

    report_form = client.get("/reports/new")
    assert report_form.status_code == 200
    assert b'<select name="category"' in report_form.data
    assert b'id="report-location-map"' in report_form.data
    assert b"Illuminazione" in report_form.data

    client.get("/logout")
    admin_login = client.post(
        "/login",
        data={"email": "demo.admin@example.test", "password": "DemoAdmin1!"},
        follow_redirects=True,
    )
    assert admin_login.status_code == 200
    assert b"Gestisci segnalazioni" in admin_login.data

    moderation = client.get("/admin/reports")
    assert moderation.status_code == 200
    assert b"Moderazione segnalazioni" in moderation.data
