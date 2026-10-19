from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import Publication, Report, ReportVersion, Support, User
from werkzeug.security import generate_password_hash


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


def create_user(app, first_name, email, password, role="UTENTE"):
    with app.app_context():
        user = User(
            first_name=first_name,
            last_name="Tester",
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            account_status="ATTIVO",
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def test_user_can_support_an_approved_report():
    app = build_test_app()
    client = app.test_client()
    owner_id = create_user(app, "Owner", "owner@example.com", "Segret0!")
    supporter_id = create_user(app, "Supporter", "supporter@example.com", "Segret0!")

    with app.app_context():
        report = Report(owner_id=owner_id, operational_status="PUBBLICATA")
        db.session.add(report)
        db.session.flush()
        version = ReportVersion(
            report_id=report.id,
            version_number=1,
            editor_id=owner_id,
            title="Parco in crisi",
            description="Esempio di supporto",
            latitude=45.0,
            longitude=9.0,
            location_origin="UTENTE",
            moderation_status="APPROVATA",
        )
        db.session.add(version)
        db.session.flush()
        db.session.add(Publication(report_id=report.id, version_id=version.id))
        db.session.commit()
        report_id = report.id

    client.post(
        "/login",
        data={"email": "supporter@example.com", "password": "Segret0!"},
        follow_redirects=True,
    )

    response = client.post(f"/reports/{report_id}/support", follow_redirects=True)

    assert response.status_code == 200
    assert b"Supporto registrato" in response.data

    with app.app_context():
        support = db.session.scalar(select(Support).where(Support.report_id == report_id, Support.user_id == supporter_id))
        assert support is not None
        assert support.active is True


def test_owner_cannot_support_own_report():
    app = build_test_app()
    client = app.test_client()
    owner_id = create_user(app, "Owner", "owner2@example.com", "Segret0!")

    with app.app_context():
        report = Report(owner_id=owner_id, operational_status="PUBBLICATA")
        db.session.add(report)
        db.session.flush()
        version = ReportVersion(
            report_id=report.id,
            version_number=1,
            editor_id=owner_id,
            title="Area verde",
            description="Non puoi sostenerla",
            latitude=45.1,
            longitude=9.1,
            location_origin="UTENTE",
            moderation_status="APPROVATA",
        )
        db.session.add(version)
        db.session.flush()
        db.session.add(Publication(report_id=report.id, version_id=version.id))
        db.session.commit()
        report_id = report.id

    client.post(
        "/login",
        data={"email": "owner2@example.com", "password": "Segret0!"},
        follow_redirects=True,
    )

    response = client.post(f"/reports/{report_id}/support", follow_redirects=True)

    assert response.status_code == 200
    assert b"Non puoi sostenere la tua segnalazione" in response.data
