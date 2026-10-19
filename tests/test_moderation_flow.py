from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import Attachment, AuditLog, ModerationDecision, Publication, Report, ReportVersion, StatusHistory, User, VersionAttachment
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


def login_as(client, email, password):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def create_user(app, name, email, password, role="UTENTE"):
    with app.app_context():
        user = User(
            first_name=name,
            last_name="Tester",
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            account_status="ATTIVO",
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def test_admin_can_approve_report_and_publish_it():
    app = build_test_app()
    client = app.test_client()

    user_id = create_user(app, "Alice", "alice@example.com", "Segret0!")
    admin_id = create_user(app, "Admin", "admin@example.com", "Segret0!", role="ADMIN")

    with app.app_context():
        report = Report(owner_id=user_id, operational_status="RICEVUTA")
        db.session.add(report)
        db.session.flush()
        version = ReportVersion(
            report_id=report.id,
            version_number=1,
            editor_id=user_id,
            title="Buche in via Roma",
            description="Descrizione di prova",
            latitude=45.4668,
            longitude=9.19,
            location_origin="UTENTE",
            moderation_status="IN_ATTESA_CONTROLLO",
        )
        db.session.add(version)
        db.session.commit()
        report_id = report.id
        version_id = version.id

    login_as(client, "admin@example.com", "Segret0!")

    response = client.post(
        f"/admin/reports/{report_id}/decision",
        data={"outcome": "APPROVATA", "reason": "Checklist verificata."},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Segnalazione approvata" in response.data

    for status in ("IN_CARICO_COMITATO", "SELEZIONATA", "INVIATA_CANDIDATI"):
        response = client.post(
            f"/admin/reports/{report_id}/status",
            data={"status": status, "reason": "Avanzamento verificato."},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Stato della segnalazione aggiornato" in response.data

    with app.app_context():
        updated_version = db.session.get(ReportVersion, version_id)
        report = db.session.get(Report, report_id)
        publication = db.session.scalar(select(Publication).where(Publication.report_id == report_id))
        history = db.session.scalars(select(StatusHistory).where(StatusHistory.report_id == report_id)).all()

        assert updated_version is not None
        assert updated_version.moderation_status == "APPROVATA"
        assert report is not None
        assert report.operational_status == "INVIATA_CANDIDATI"
        assert publication is not None
        assert publication.version_id == version_id
        assert len(history) == 4
        assert db.session.scalar(
            select(AuditLog).where(AuditLog.action == "STATO_SEGNALAZIONE_AGGIORNATO")
        ) is not None


def test_admin_cannot_skip_report_lifecycle_stages():
    app = build_test_app()
    client = app.test_client()
    owner_id = create_user(app, "Owner", "owner@example.com", "Segret0!")
    create_user(app, "Admin", "admin@example.com", "Segret0!", role="ADMIN")

    with app.app_context():
        report = Report(owner_id=owner_id, operational_status="PUBBLICATA")
        db.session.add(report)
        db.session.flush()
        version = ReportVersion(
            report_id=report.id,
            version_number=1,
            editor_id=owner_id,
            title="Segnalazione pubblicata",
            description="Test transizione non valida",
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

    login_as(client, "admin@example.com", "Segret0!")
    response = client.post(
        f"/admin/reports/{report_id}/status",
        data={"status": "INVIATA_CANDIDATI"},
        follow_redirects=True,
    )

    assert b"Transizione di stato non consentita" in response.data
    with app.app_context():
        report = db.session.get(Report, report_id)
        assert report.operational_status == "PUBBLICATA"


def test_admin_cannot_moderate_own_report():
    app = build_test_app()
    client = app.test_client()
    admin_id = create_user(app, "Admin", "admin-owner@example.com", "Segret0!", role="ADMIN")

    with app.app_context():
        report = Report(owner_id=admin_id, operational_status="RICEVUTA")
        db.session.add(report)
        db.session.flush()
        version = ReportVersion(
            report_id=report.id,
            version_number=1,
            editor_id=admin_id,
            title="Segnalazione dello stesso admin",
            description="Non deve poterla approvare.",
            latitude=45.0,
            longitude=9.0,
            location_origin="UTENTE",
            moderation_status="IN_ATTESA_CONTROLLO",
        )
        db.session.add(version)
        db.session.commit()
        report_id = report.id

    login_as(client, "admin-owner@example.com", "Segret0!")
    response = client.post(
        f"/admin/reports/{report_id}/decision",
        data={"outcome": "APPROVATA"},
        follow_redirects=True,
    )

    assert b"Non puoi moderare una tua segnalazione" in response.data
    with app.app_context():
        report = db.session.get(Report, report_id)
        assert report.operational_status == "RICEVUTA"
        assert db.session.scalar(select(ModerationDecision)) is None


def test_publish_only_approved_reports_are_visible_publicly():
    app = build_test_app()
    client = app.test_client()

    user_id = create_user(app, "Bob", "bob@example.com", "Segret0!")

    with app.app_context():
        report = Report(owner_id=user_id, operational_status="RICEVUTA")
        db.session.add(report)
        db.session.flush()
        approved = ReportVersion(
            report_id=report.id,
            version_number=1,
            editor_id=user_id,
            title="Via pulita",
            description="Segnalazione già approvata",
            latitude=45.1,
            longitude=9.1,
            location_origin="UTENTE",
            moderation_status="APPROVATA",
        )
        db.session.add(approved)
        db.session.flush()
        db.session.add(Publication(report_id=report.id, version_id=approved.id))
        report.operational_status = "PUBBLICATA"
        db.session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Via pulita" in response.data


def test_public_report_displays_and_serves_its_uploaded_photo(tmp_path):
    app = build_test_app()
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    client = app.test_client()
    user_id = create_user(app, "Carla", "carla@example.com", "Segret0!")
    image_bytes = b"verified-public-photo"
    (tmp_path / "public-proof.jpg").write_bytes(image_bytes)

    with app.app_context():
        report = Report(owner_id=user_id, operational_status="PUBBLICATA")
        db.session.add(report)
        db.session.flush()
        version = ReportVersion(
            report_id=report.id,
            version_number=1,
            editor_id=user_id,
            title="Lampione spento",
            description="Foto allegata alla segnalazione pubblicata.",
            latitude=45.2,
            longitude=9.2,
            location_origin="UTENTE",
            moderation_status="APPROVATA",
        )
        db.session.add(version)
        db.session.flush()
        attachment = Attachment(
            report_id=report.id,
            uploader_id=user_id,
            media_type="FOTO",
            content_type="image/jpeg",
            storage_ref="public-proof.jpg",
            size_bytes=len(image_bytes),
            checksum="verified-checksum",
            file_status="DISPONIBILE",
        )
        db.session.add(attachment)
        db.session.flush()
        db.session.add_all(
            [
                VersionAttachment(
                    version_id=version.id,
                    attachment_id=attachment.id,
                    report_id=report.id,
                    order=0,
                ),
                Publication(report_id=report.id, version_id=version.id),
            ]
        )
        db.session.commit()
        report_id = report.id
        attachment_id = attachment.id

    response = client.get("/")
    assert b"Lampione spento" in response.data
    assert f"/reports/{report_id}/attachments/{attachment_id}".encode() in response.data

    media_response = client.get(f"/reports/{report_id}/attachments/{attachment_id}")
    assert media_response.status_code == 200
    assert media_response.data == image_bytes
