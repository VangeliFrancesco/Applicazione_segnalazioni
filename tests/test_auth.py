from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import AuditLog, User


def build_test_app():
    app = create_app(
        {
            "TESTING": True,
            "PREVIEW_MODE": False,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
        }
    )
    with app.app_context():
        db.create_all()
    return app


def test_user_can_register_and_login():
    app = build_test_app()
    client = app.test_client()

    response = client.post(
        "/register",
        data={
            "first_name": "Mario",
            "last_name": "Rossi",
            "email": "mario@example.com",
            "password": "Segret0!",
            "confirm_password": "Segret0!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Registrazione completata" in response.data

    with app.app_context():
        user = db.session.scalar(select(User).where(User.email == "mario@example.com"))
        assert user is not None
        assert user.role == "UTENTE"
        assert db.session.scalar(select(AuditLog).where(AuditLog.action == "UTENTE_REGISTRATO")) is not None

    login_response = client.post(
        "/login",
        data={"email": "mario@example.com", "password": "Segret0!"},
        follow_redirects=True,
    )

    assert login_response.status_code == 200
    assert b"Dashboard" in login_response.data

    with app.app_context():
        assert db.session.scalar(select(AuditLog).where(AuditLog.action == "ACCESSO_ESEGUITO")) is not None


def test_admin_can_be_provisioned_only_through_cli():
    app = build_test_app()
    result = app.test_cli_runner().invoke(
        args=["create-admin"],
        input="Admin\nOperatore\nadmin@example.com\nSegret0!\nSegret0!\n",
    )

    assert result.exit_code == 0
    with app.app_context():
        admin = db.session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        assert admin.role == "ADMIN"
        assert db.session.scalar(
            select(AuditLog).where(AuditLog.action == "AMMINISTRATORE_CREATO")
        ) is not None


def test_unregistered_user_cannot_access_dashboard():
    app = build_test_app()
    client = app.test_client()

    response = client.get("/dashboard", follow_redirects=True)

    assert response.status_code == 200
    assert b"Accedi" in response.data


def test_admin_page_requires_admin_role():
    app = build_test_app()
    client = app.test_client()

    client.post(
        "/register",
        data={
            "first_name": "Luca",
            "last_name": "Bianchi",
            "email": "luca@example.com",
            "password": "Segret0!",
            "confirm_password": "Segret0!",
        },
        follow_redirects=True,
    )

    client.post(
        "/login",
        data={"email": "luca@example.com", "password": "Segret0!"},
        follow_redirects=True,
    )

    response = client.get("/admin", follow_redirects=True)

    assert response.status_code == 200
    assert b"Accesso non consentito" in response.data
