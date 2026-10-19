from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "utente"
    __table_args__ = (
        CheckConstraint("ruolo IN ('UTENTE', 'ADMIN')", name="ck_utente_ruolo"),
        CheckConstraint("stato_account IN ('ATTIVO', 'DISATTIVATO')", name="ck_utente_stato"),
    )

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    first_name = db.Column("nome", String(100), nullable=False)
    last_name = db.Column("cognome", String(100), nullable=False)
    email = db.Column(String(254), nullable=False, unique=True)
    password_hash = db.Column(String(255), nullable=False)
    role = db.Column("ruolo", String(16), nullable=False, default="UTENTE")
    account_status = db.Column("stato_account", String(16), nullable=False, default="ATTIVO")
    registered_at = db.Column("data_registrazione", DateTime, nullable=False, default=utcnow)
    email_verified_at = db.Column("data_verifica_email", DateTime)
    neighborhood_id = db.Column("quartiere_id", ForeignKey("quartiere.id", ondelete="SET NULL"))


class Neighborhood(db.Model):
    __tablename__ = "quartiere"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    name = db.Column("nome", String(120), nullable=False, unique=True)
    code = db.Column("codice", String(32), nullable=False, unique=True)


class Report(db.Model):
    __tablename__ = "segnalazione"
    __table_args__ = (
        CheckConstraint(
            "stato_operativo IN ('BOZZA', 'RICEVUTA', 'PUBBLICATA', "
            "'IN_CARICO_COMITATO', 'SELEZIONATA', 'INVIATA_CANDIDATI', "
            "'ARCHIVIATA', 'RITIRATA')",
            name="ck_segnalazione_stato",
        ),
        Index("ix_segnalazione_autore", "autore_id"),
    )

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column("autore_id", ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False)
    operational_status = db.Column("stato_operativo", String(32), nullable=False, default="BOZZA")
    created_at = db.Column("data_creazione", DateTime, nullable=False, default=utcnow)
    updated_at = db.Column("data_ultimo_aggiornamento", DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class ReportVersion(db.Model):
    __tablename__ = "versione"
    __table_args__ = (
        UniqueConstraint("segnalazione_id", "numero_versione", name="uq_versione_numero"),
        UniqueConstraint("id", "segnalazione_id", name="uq_versione_id_segnalazione"),
        CheckConstraint("numero_versione > 0", name="ck_versione_numero_positivo"),
        CheckConstraint("latitudine BETWEEN -90 AND 90", name="ck_versione_latitudine"),
        CheckConstraint("longitudine BETWEEN -180 AND 180", name="ck_versione_longitudine"),
        CheckConstraint(
            "stato_moderazione IN ('IN_ATTESA_CONTROLLO', 'IN_REVISIONE_ADMIN', "
            "'IN_ATTESA_CHIARIMENTI', 'APPROVATA', 'RIFIUTATA')",
            name="ck_versione_moderazione",
        ),
    )

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    report_id = db.Column("segnalazione_id", ForeignKey("segnalazione.id", ondelete="RESTRICT"), nullable=False)
    version_number = db.Column("numero_versione", Integer, nullable=False)
    editor_id = db.Column("redattore_id", ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False)
    title = db.Column("titolo", String(180), nullable=False)
    description = db.Column("descrizione", Text, nullable=False)
    latitude = db.Column("latitudine", Float, nullable=False)
    longitude = db.Column("longitudine", Float, nullable=False)
    address = db.Column("indirizzo", String(255))
    location_origin = db.Column("origine_localizzazione", String(32), nullable=False)
    neighborhood_id = db.Column("quartiere_id", ForeignKey("quartiere.id", ondelete="SET NULL"))
    moderation_status = db.Column("stato_moderazione", String(32), nullable=False, default="IN_ATTESA_CONTROLLO")
    created_at = db.Column("data_creazione", DateTime, nullable=False, default=utcnow)
    submitted_at = db.Column("data_invio", DateTime)
    change_reason = db.Column("motivo_modifica", Text)


class Attachment(db.Model):
    __tablename__ = "allegato"
    __table_args__ = (
        UniqueConstraint("id", "segnalazione_id", name="uq_allegato_id_segnalazione"),
        CheckConstraint("tipo IN ('FOTO', 'VIDEO')", name="ck_allegato_tipo"),
        CheckConstraint("dimensione > 0", name="ck_allegato_dimensione"),
        CheckConstraint("durata_secondi IS NULL OR durata_secondi > 0", name="ck_allegato_durata"),
        CheckConstraint("stato_file IN ('TEMPORANEO', 'DISPONIBILE', 'RIFIUTATO', 'ELIMINATO')", name="ck_allegato_stato"),
        Index("ix_allegato_segnalazione", "segnalazione_id"),
    )

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    report_id = db.Column("segnalazione_id", ForeignKey("segnalazione.id", ondelete="RESTRICT"), nullable=False)
    uploader_id = db.Column("caricatore_id", ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False)
    media_type = db.Column("tipo", String(8), nullable=False)
    content_type = db.Column("tipo_contenuto", String(120), nullable=False)
    storage_ref = db.Column("riferimento_storage", String(512), nullable=False, unique=True)
    size_bytes = db.Column("dimensione", Integer, nullable=False)
    duration_seconds = db.Column("durata_secondi", Integer)
    checksum = db.Column(String(64), nullable=False)
    file_status = db.Column("stato_file", String(16), nullable=False, default="TEMPORANEO")
    uploaded_at = db.Column("data_caricamento", DateTime, nullable=False, default=utcnow)


class AttachmentMetadata(db.Model):
    __tablename__ = "metadati_allegato"
    __table_args__ = (
        CheckConstraint(
            "latitudine_estratta IS NULL OR latitudine_estratta BETWEEN -90 AND 90",
            name="ck_metadati_latitudine",
        ),
        CheckConstraint(
            "longitudine_estratta IS NULL OR longitudine_estratta BETWEEN -180 AND 180",
            name="ck_metadati_longitudine",
        ),
    )

    attachment_id = db.Column(ForeignKey("allegato.id", ondelete="CASCADE"), primary_key=True)
    extracted_latitude = db.Column("latitudine_estratta", Float)
    extracted_longitude = db.Column("longitudine_estratta", Float)
    declared_original_date = db.Column("data_originale_dichiarata", DateTime)
    technical_info = db.Column("informazioni_tecniche", JSON)
    extracted_at = db.Column("data_estrazione", DateTime, nullable=False, default=utcnow)


class Category(db.Model):
    __tablename__ = "categoria"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    name = db.Column("nome", String(100), nullable=False, unique=True)
    description = db.Column("descrizione", Text)
    active = db.Column("attiva", Boolean, nullable=False, default=True)


class VersionAttachment(db.Model):
    __tablename__ = "versione_allegato"
    __table_args__ = (
        ForeignKeyConstraint(
            ["versione_id", "segnalazione_id"],
            ["versione.id", "versione.segnalazione_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["allegato_id", "segnalazione_id"],
            ["allegato.id", "allegato.segnalazione_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("versione_id", "ordine", name="uq_versione_allegato_ordine"),
        CheckConstraint("ordine >= 0", name="ck_versione_allegato_ordine"),
    )

    version_id = db.Column("versione_id", Integer, primary_key=True)
    attachment_id = db.Column("allegato_id", Integer, primary_key=True)
    report_id = db.Column("segnalazione_id", Integer, nullable=False)
    order = db.Column("ordine", Integer, nullable=False)


class CategoryAssignment(db.Model):
    __tablename__ = "assegnazione_categoria"
    __table_args__ = (
        CheckConstraint("origine IN ('UTENTE', 'IA', 'ADMIN')", name="ck_assegnazione_origine"),
        CheckConstraint("indicazione IN ('SELEZIONATA', 'SUGGERITA', 'CONFERMATA', 'ESCLUSA')", name="ck_assegnazione_indicazione"),
        CheckConstraint(
            "(origine = 'UTENTE' AND indicazione = 'SELEZIONATA') OR "
            "(origine = 'IA' AND indicazione = 'SUGGERITA') OR "
            "(origine = 'ADMIN' AND indicazione IN ('CONFERMATA', 'ESCLUSA'))",
            name="ck_assegnazione_coerenza",
        ),
        CheckConstraint("confidenza IS NULL OR confidenza BETWEEN 0 AND 1", name="ck_assegnazione_confidenza"),
    )

    version_id = db.Column("versione_id", ForeignKey("versione.id", ondelete="CASCADE"), primary_key=True)
    category_id = db.Column("categoria_id", ForeignKey("categoria.id", ondelete="RESTRICT"), primary_key=True)
    origin = db.Column("origine", String(8), primary_key=True)
    indication = db.Column("indicazione", String(12), nullable=False)
    confidence = db.Column("confidenza", Float)
    assigned_at = db.Column("data_assegnazione", DateTime, nullable=False, default=utcnow)


class Support(db.Model):
    __tablename__ = "sostegno"
    __table_args__ = (
        CheckConstraint("attivo IN (0, 1)", name="ck_sostegno_attivo"),
        Index("ix_sostegno_classifica", "segnalazione_id", "attivo"),
    )

    user_id = db.Column("utente_id", ForeignKey("utente.id", ondelete="RESTRICT"), primary_key=True)
    report_id = db.Column("segnalazione_id", ForeignKey("segnalazione.id", ondelete="RESTRICT"), primary_key=True)
    active = db.Column("attivo", Boolean, nullable=False, default=True)
    created_at = db.Column("data_creazione", DateTime, nullable=False, default=utcnow)
    updated_at = db.Column("data_aggiornamento", DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Publication(db.Model):
    __tablename__ = "pubblicazione"
    __table_args__ = (
        ForeignKeyConstraint(
            ["versione_id", "segnalazione_id"],
            ["versione.id", "versione.segnalazione_id"],
            ondelete="RESTRICT",
        ),
    )

    report_id = db.Column("segnalazione_id", ForeignKey("segnalazione.id", ondelete="CASCADE"), primary_key=True)
    version_id = db.Column("versione_id", Integer, nullable=False, unique=True)
    published_at = db.Column("data_pubblicazione", DateTime, nullable=False, default=utcnow)


class EmailVerification(db.Model):
    __tablename__ = "verifica_email"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    user_id = db.Column("utente_id", ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False)
    token_hash = db.Column(String(64), nullable=False, unique=True)
    created_at = db.Column("data_creazione", DateTime, nullable=False, default=utcnow)
    expires_at = db.Column("data_scadenza", DateTime, nullable=False)
    consumed_at = db.Column("data_utilizzo", DateTime)


class UserSession(db.Model):
    __tablename__ = "sessione_utente"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    user_id = db.Column("utente_id", ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False)
    token_hash = db.Column(String(64), nullable=False, unique=True)
    created_at = db.Column("data_creazione", DateTime, nullable=False, default=utcnow)
    expires_at = db.Column("data_scadenza", DateTime, nullable=False)
    revoked_at = db.Column("data_revoca", DateTime)


class AuditLog(db.Model):
    __tablename__ = "log_audit"
    __table_args__ = (Index("ix_log_audit_entita", "tipo_entita", "id_entita", "data_evento"),)

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    actor_id = db.Column("attore_id", ForeignKey("utente.id", ondelete="SET NULL"))
    action = db.Column("azione", String(80), nullable=False)
    entity_type = db.Column("tipo_entita", String(40), nullable=False)
    entity_id = db.Column("id_entita", Integer)
    details = db.Column("dettagli", JSON)
    occurred_at = db.Column("data_evento", DateTime, nullable=False, default=utcnow)


class StatusHistory(db.Model):
    __tablename__ = "cronologia_stato"
    __table_args__ = (Index("ix_cronologia_segnalazione", "segnalazione_id", "data_evento"),)

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    report_id = db.Column("segnalazione_id", ForeignKey("segnalazione.id", ondelete="RESTRICT"), nullable=False)
    actor_id = db.Column("attore_id", ForeignKey("utente.id", ondelete="SET NULL"))
    previous_status = db.Column("stato_precedente", String(32))
    new_status = db.Column("stato_nuovo", String(32), nullable=False)
    reason = db.Column("motivazione", Text)
    occurred_at = db.Column("data_evento", DateTime, nullable=False, default=utcnow)


class ModerationDecision(db.Model):
    __tablename__ = "decisione_moderazione"
    __table_args__ = (
        CheckConstraint("esito IN ('APPROVATA', 'RIFIUTATA', 'RICHIESTE_MODIFICHE')", name="ck_decisione_esito"),
        Index("ix_decisione_versione", "versione_id", "data_decisione"),
    )

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    version_id = db.Column("versione_id", ForeignKey("versione.id", ondelete="RESTRICT"), nullable=False)
    admin_id = db.Column(ForeignKey("utente.id", ondelete="RESTRICT"), nullable=False)
    outcome = db.Column("esito", String(24), nullable=False)
    reason = db.Column("motivazione", Text, nullable=False)
    decided_at = db.Column("data_decisione", DateTime, nullable=False, default=utcnow)