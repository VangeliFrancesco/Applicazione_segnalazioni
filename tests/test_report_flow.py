from io import BytesIO

from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import Attachment, Category, Report, ReportVersion, VersionAttachment


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


def test_authenticated_user_can_create_a_report():
    app = build_test_app()
    client = app.test_client()

    client.post(
        "/register",
        data={
            "first_name": "Alice",
            "last_name": "Verdi",
            "email": "alice@example.com",
            "password": "Segret0!",
            "confirm_password": "Segret0!",
        },
        follow_redirects=True,
    )
    client.post(
        "/login",
        data={"email": "alice@example.com", "password": "Segret0!"},
        follow_redirects=True,
    )

    response = client.post(
        "/reports/new",
        data={
            "title": "Buche in via Roma",
            "description": "C'è una buca pericolosa vicino al passaggio pedonale.",
            "category": "Strade e marciapiedi",
            "latitude": "45.4668",
            "longitude": "9.1900",
            "media_type": "FOTO",
            "media_file": (BytesIO(b"prova foto"), "foto.jpg"),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Segnalazione inviata" in response.data

    with app.app_context():
        report = db.session.scalar(select(Report))
        version = db.session.scalar(select(ReportVersion))
        attachment = db.session.scalar(select(Attachment))
        attachment_link = db.session.scalar(select(VersionAttachment))
        category = db.session.scalar(select(Category).where(Category.name == "Strade e marciapiedi"))

        assert report is not None
        assert version is not None
        assert version.title == "Buche in via Roma"
        assert category is not None
        assert version.report_id == report.id
        assert attachment is not None
        assert attachment.size_bytes == len(b"prova foto")
        assert attachment.checksum != ""
        assert attachment_link is not None
        assert attachment_link.version_id == version.id
        assert attachment_link.attachment_id == attachment.id


def test_report_form_keeps_default_categories_and_location_picker():
    app = build_test_app()
    client = app.test_client()
    with app.app_context():
        db.session.add(Category(name="Illuminazione", active=True))
        db.session.commit()

    client.post(
        "/register",
        data={
            "first_name": "Luca",
            "last_name": "Verdi",
            "email": "luca@example.com",
            "password": "Segret0!",
            "confirm_password": "Segret0!",
        },
    )
    client.post("/login", data={"email": "luca@example.com", "password": "Segret0!"})
    response = client.get("/reports/new")

    assert response.status_code == 200
    assert b"Illuminazione" in response.data
    assert b"Strade e marciapiedi" in response.data
    assert b"report-location-map" in response.data
    assert b"use-current-location" in response.data
