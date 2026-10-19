import os

import click
from flask import Flask
from sqlalchemy import URL
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app.extensions import db, migrate


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        PREVIEW_MODE=os.getenv("PREVIEW_MODE", "0") == "1",
        DB_HOST=os.getenv("DB_HOST"),
        DB_PORT=os.getenv("DB_PORT", "24198"),
        DB_NAME=os.getenv("DB_NAME"),
        DB_USER=os.getenv("DB_USER"),
        DB_PASSWORD=os.getenv("DB_PASSWORD"),
        DB_SSL_MODE=os.getenv("DB_SSL_MODE", "VERIFY_IDENTITY"),
        DB_SSL_CA=os.getenv("DB_SSL_CA"),
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", os.path.join(app.instance_path, "uploads")),
        MAX_CONTENT_LENGTH=64 * 1024 * 1024,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    if app.config["PREVIEW_MODE"]:
        app.config["SECRET_KEY"] = app.config["SECRET_KEY"] or "preview-only-no-authentication"
        app.config["DATABASE_CONFIGURED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
        app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "preview_uploads")
        db.init_app(app)
        migrate.init_app(app, db)
    else:
        explicit_database_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
        if not explicit_database_uri:
            required = ("SECRET_KEY", "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_SSL_CA")
            missing = [name for name in required if not app.config.get(name)]
            if missing:
                raise RuntimeError(f"Configurazione obbligatoria mancante: {', '.join(missing)}")
            if app.config["DB_SSL_MODE"] != "VERIFY_IDENTITY":
                raise RuntimeError("DB_SSL_MODE deve essere VERIFY_IDENTITY")

            app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
                "mysql+mysqlconnector",
                username=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                host=app.config["DB_HOST"],
                port=int(app.config["DB_PORT"]),
                database=app.config["DB_NAME"],
            )
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "connect_args": {
                    "ssl_ca": app.config["DB_SSL_CA"],
                    "ssl_verify_cert": True,
                    "ssl_verify_identity": True,
                }
            }

        app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {})
        app.config["DATABASE_CONFIGURED"] = True

        db.init_app(app)
        migrate.init_app(app, db)

    from app import models  # noqa: F401
    from app.routes import main

    app.register_blueprint(main)

    if app.config["PREVIEW_MODE"]:
        from app.models import Category, CategoryAssignment, Publication, Report, ReportVersion, User, utcnow

        with app.app_context():
            db.create_all()
            demo_user = db.session.scalar(select(User).where(User.email == "demo.utente@example.test"))
            if demo_user is None:
                demo_user = User(
                    first_name="Giulia",
                    last_name="Demo",
                    email="demo.utente@example.test",
                    password_hash=generate_password_hash("DemoUtente1!"),
                    role="UTENTE",
                    account_status="ATTIVO",
                )
                demo_admin = User(
                    first_name="Admin",
                    last_name="Demo",
                    email="demo.admin@example.test",
                    password_hash=generate_password_hash("DemoAdmin1!"),
                    role="ADMIN",
                    account_status="ATTIVO",
                )
                db.session.add_all([demo_user, demo_admin])
                db.session.flush()

                report = Report(owner_id=demo_admin.id, operational_status="PUBBLICATA")
                db.session.add(report)
                db.session.flush()
                version = ReportVersion(
                    report_id=report.id,
                    version_number=1,
                    editor_id=demo_admin.id,
                    title="Attraversamento pedonale poco illuminato",
                    description="La sera l’attraversamento vicino al parco è poco visibile e richiede più illuminazione.",
                    latitude=45.4642,
                    longitude=9.19,
                    location_origin="UTENTE",
                    moderation_status="APPROVATA",
                    submitted_at=utcnow(),
                )
                db.session.add(version)
                db.session.flush()
                category = Category(name="Illuminazione", description="Illuminazione pubblica")
                db.session.add(category)
                db.session.flush()
                db.session.add_all(
                    [
                        CategoryAssignment(
                            version_id=version.id,
                            category_id=category.id,
                            origin="UTENTE",
                            indication="SELEZIONATA",
                            confidence=1.0,
                        ),
                        Publication(report_id=report.id, version_id=version.id),
                    ]
                )
                db.session.commit()

    @app.cli.command("create-admin")
    def create_admin():
        """Create an administrator without exposing role escalation publicly."""
        if not app.config["DATABASE_CONFIGURED"]:
            raise click.ClickException("La modalità preview non può creare amministratori.")

        from app.models import AuditLog, User

        first_name = click.prompt("Nome")
        last_name = click.prompt("Cognome")
        email = click.prompt("Email").strip().lower()
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if len(password) < 8:
            raise click.ClickException("La password deve avere almeno 8 caratteri.")
        if db.session.scalar(select(User).where(User.email == email)):
            raise click.ClickException("Esiste già un utente con questa email.")

        admin = User(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email,
            password_hash=generate_password_hash(password),
            role="ADMIN",
            account_status="ATTIVO",
        )
        db.session.add(admin)
        db.session.flush()
        db.session.add(
            AuditLog(
                actor_id=admin.id,
                action="AMMINISTRATORE_CREATO",
                entity_type="utente",
                entity_id=admin.id,
                details={"email": email},
            )
        )
        db.session.commit()
        click.echo(f"Amministratore creato: {email}")

    return app