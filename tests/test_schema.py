import importlib.util
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import create_mock_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app import create_app, models
from app.extensions import db


def valid_config(**overrides):
    config = {
        "SECRET_KEY": "test-secret-not-used-for-authentication",
        "DB_HOST": "mysql.example.invalid",
        "DB_PORT": "3306",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_SSL_MODE": "VERIFY_IDENTITY",
        "DB_SSL_CA": "/tmp/test-ca.pem",
    }
    config.update(overrides)
    return config


def test_app_requires_database_and_secret_configuration():
    with pytest.raises(RuntimeError, match="Configurazione obbligatoria mancante"):
        create_app({"TESTING": True, "SECRET_KEY": "test-only"})


def test_preview_home_renders_with_isolated_database():
    app = create_app({"TESTING": True, "PREVIEW_MODE": True})

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"
    assert app.config["DATABASE_CONFIGURED"] is False
    assert b"Anteprima interattiva" in response.data
    assert b"Attraversamento pedonale poco illuminato" in response.data
    assert b"Nessuna segnalazione pubblica" not in response.data


def test_app_requires_verified_tls():
    with pytest.raises(RuntimeError, match="VERIFY_IDENTITY"):
        create_app(valid_config(DB_SSL_MODE="DISABLED"))


def test_app_configures_mysql_with_certificate_and_hostname_verification():
    app = create_app(valid_config())

    assert app.config["SQLALCHEMY_DATABASE_URI"].drivername == "mysql+mysqlconnector"
    assert app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] == {
        "ssl_ca": "/tmp/test-ca.pem",
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
    }


def test_all_models_compile_for_mysql():
    tables = db.metadata.sorted_tables

    assert len(tables) == 16
    for table in tables:
        str(CreateTable(table).compile(dialect=mysql.dialect()))


def test_support_is_unique_per_user_and_report():
    support = db.metadata.tables["sostegno"]

    assert tuple(column.name for column in support.primary_key.columns) == (
        "utente_id",
        "segnalazione_id",
    )


def test_associations_keep_version_and_attachment_in_same_report():
    association = db.metadata.tables["versione_allegato"]
    composite_foreign_keys = [
        constraint
        for constraint in association.foreign_key_constraints
        if len(constraint.columns) == 2
    ]

    assert len(composite_foreign_keys) == 2


def test_publication_references_version_of_same_report():
    publication = db.metadata.tables["pubblicazione"]
    composite_foreign_keys = [
        constraint
        for constraint in publication.foreign_key_constraints
        if len(constraint.columns) == 2
    ]

    assert len(composite_foreign_keys) == 1
    assert publication.primary_key.columns.keys() == ["segnalazione_id"]


def test_tokens_are_stored_only_as_hashes():
    verification = db.metadata.tables["verifica_email"]
    session = db.metadata.tables["sessione_utente"]

    assert "token_hash" in verification.c
    assert "token" not in verification.c
    assert "token_hash" in session.c
    assert "token" not in session.c


def test_category_assignment_has_one_indication_per_origin():
    assignment = db.metadata.tables["assegnazione_categoria"]

    assert tuple(column.name for column in assignment.primary_key.columns) == (
        "versione_id",
        "categoria_id",
        "origine",
    )


def test_initial_migration_matches_model_metadata(monkeypatch):
    migration_path = Path(__file__).parents[1] / "migrations" / "versions" / "0001_core_schema.py"
    spec = importlib.util.spec_from_file_location("initial_schema_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    actual_statements = []
    monkeypatch.setattr(migration.op, "execute", actual_statements.append)
    migration.upgrade()

    expected_statements = []
    engine = create_mock_engine(
        "mysql://",
        lambda statement, *args, **kwargs: expected_statements.append(
            str(statement.compile(dialect=engine.dialect))
        ),
    )
    db.metadata.create_all(engine)

    normalize = lambda statement: " ".join(statement.split()).rstrip(";")
    assert Counter(map(normalize, actual_statements)) == Counter(map(normalize, expected_statements))