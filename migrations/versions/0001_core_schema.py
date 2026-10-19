"""Create the approved core schema and minimal account/audit extensions."""

from alembic import op


revision = "0001_core_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    statements = (
        """CREATE TABLE quartiere (
            id INTEGER NOT NULL AUTO_INCREMENT,
            nome VARCHAR(120) NOT NULL,
            codice VARCHAR(32) NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (nome),
            UNIQUE (codice)
        )""",
        """CREATE TABLE categoria (
            id INTEGER NOT NULL AUTO_INCREMENT,
            nome VARCHAR(100) NOT NULL,
            descrizione TEXT,
            attiva BOOL NOT NULL,
            PRIMARY KEY (id),
            UNIQUE (nome)
        )""",
        """CREATE TABLE utente (
            id INTEGER NOT NULL AUTO_INCREMENT,
            nome VARCHAR(100) NOT NULL,
            cognome VARCHAR(100) NOT NULL,
            email VARCHAR(254) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            ruolo VARCHAR(16) NOT NULL,
            stato_account VARCHAR(16) NOT NULL,
            data_registrazione DATETIME NOT NULL,
            data_verifica_email DATETIME,
            quartiere_id INTEGER,
            PRIMARY KEY (id),
            CONSTRAINT ck_utente_ruolo CHECK (ruolo IN ('UTENTE', 'ADMIN')),
            CONSTRAINT ck_utente_stato CHECK (stato_account IN ('ATTIVO', 'DISATTIVATO')),
            UNIQUE (email),
            FOREIGN KEY(quartiere_id) REFERENCES quartiere (id) ON DELETE SET NULL
        )""",
        """CREATE TABLE segnalazione (
            id INTEGER NOT NULL AUTO_INCREMENT,
            autore_id INTEGER NOT NULL,
            stato_operativo VARCHAR(32) NOT NULL,
            data_creazione DATETIME NOT NULL,
            data_ultimo_aggiornamento DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_segnalazione_stato CHECK (stato_operativo IN ('BOZZA', 'RICEVUTA', 'PUBBLICATA', 'IN_CARICO_COMITATO', 'SELEZIONATA', 'INVIATA_CANDIDATI', 'ARCHIVIATA', 'RITIRATA')),
            FOREIGN KEY(autore_id) REFERENCES utente (id) ON DELETE RESTRICT
        )""",
        """CREATE TABLE verifica_email (
            id INTEGER NOT NULL AUTO_INCREMENT,
            utente_id INTEGER NOT NULL,
            token_hash VARCHAR(64) NOT NULL,
            data_creazione DATETIME NOT NULL,
            data_scadenza DATETIME NOT NULL,
            data_utilizzo DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(utente_id) REFERENCES utente (id) ON DELETE RESTRICT,
            UNIQUE (token_hash)
        )""",
        """CREATE TABLE sessione_utente (
            id INTEGER NOT NULL AUTO_INCREMENT,
            utente_id INTEGER NOT NULL,
            token_hash VARCHAR(64) NOT NULL,
            data_creazione DATETIME NOT NULL,
            data_scadenza DATETIME NOT NULL,
            data_revoca DATETIME,
            PRIMARY KEY (id),
            FOREIGN KEY(utente_id) REFERENCES utente (id) ON DELETE RESTRICT,
            UNIQUE (token_hash)
        )""",
        """CREATE TABLE log_audit (
            id INTEGER NOT NULL AUTO_INCREMENT,
            attore_id INTEGER,
            azione VARCHAR(80) NOT NULL,
            tipo_entita VARCHAR(40) NOT NULL,
            id_entita INTEGER,
            dettagli JSON,
            data_evento DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(attore_id) REFERENCES utente (id) ON DELETE SET NULL
        )""",
        """CREATE TABLE versione (
            id INTEGER NOT NULL AUTO_INCREMENT,
            segnalazione_id INTEGER NOT NULL,
            numero_versione INTEGER NOT NULL,
            redattore_id INTEGER NOT NULL,
            titolo VARCHAR(180) NOT NULL,
            descrizione TEXT NOT NULL,
            latitudine FLOAT NOT NULL,
            longitudine FLOAT NOT NULL,
            indirizzo VARCHAR(255),
            origine_localizzazione VARCHAR(32) NOT NULL,
            quartiere_id INTEGER,
            stato_moderazione VARCHAR(32) NOT NULL,
            data_creazione DATETIME NOT NULL,
            data_invio DATETIME,
            motivo_modifica TEXT,
            PRIMARY KEY (id),
            CONSTRAINT uq_versione_numero UNIQUE (segnalazione_id, numero_versione),
            CONSTRAINT uq_versione_id_segnalazione UNIQUE (id, segnalazione_id),
            CONSTRAINT ck_versione_numero_positivo CHECK (numero_versione > 0),
            CONSTRAINT ck_versione_latitudine CHECK (latitudine BETWEEN -90 AND 90),
            CONSTRAINT ck_versione_longitudine CHECK (longitudine BETWEEN -180 AND 180),
            CONSTRAINT ck_versione_moderazione CHECK (stato_moderazione IN ('IN_ATTESA_CONTROLLO', 'IN_REVISIONE_ADMIN', 'IN_ATTESA_CHIARIMENTI', 'APPROVATA', 'RIFIUTATA')),
            FOREIGN KEY(segnalazione_id) REFERENCES segnalazione (id) ON DELETE RESTRICT,
            FOREIGN KEY(redattore_id) REFERENCES utente (id) ON DELETE RESTRICT,
            FOREIGN KEY(quartiere_id) REFERENCES quartiere (id) ON DELETE SET NULL
        )""",
        """CREATE TABLE allegato (
            id INTEGER NOT NULL AUTO_INCREMENT,
            segnalazione_id INTEGER NOT NULL,
            caricatore_id INTEGER NOT NULL,
            tipo VARCHAR(8) NOT NULL,
            tipo_contenuto VARCHAR(120) NOT NULL,
            riferimento_storage VARCHAR(512) NOT NULL,
            dimensione INTEGER NOT NULL,
            durata_secondi INTEGER,
            checksum VARCHAR(64) NOT NULL,
            stato_file VARCHAR(16) NOT NULL,
            data_caricamento DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_allegato_id_segnalazione UNIQUE (id, segnalazione_id),
            CONSTRAINT ck_allegato_tipo CHECK (tipo IN ('FOTO', 'VIDEO')),
            CONSTRAINT ck_allegato_dimensione CHECK (dimensione > 0),
            CONSTRAINT ck_allegato_durata CHECK (durata_secondi IS NULL OR durata_secondi > 0),
            CONSTRAINT ck_allegato_stato CHECK (stato_file IN ('TEMPORANEO', 'DISPONIBILE', 'RIFIUTATO', 'ELIMINATO')),
            FOREIGN KEY(segnalazione_id) REFERENCES segnalazione (id) ON DELETE RESTRICT,
            FOREIGN KEY(caricatore_id) REFERENCES utente (id) ON DELETE RESTRICT,
            UNIQUE (riferimento_storage)
        )""",
        """CREATE TABLE sostegno (
            utente_id INTEGER NOT NULL,
            segnalazione_id INTEGER NOT NULL,
            attivo BOOL NOT NULL,
            data_creazione DATETIME NOT NULL,
            data_aggiornamento DATETIME NOT NULL,
            PRIMARY KEY (utente_id, segnalazione_id),
            CONSTRAINT ck_sostegno_attivo CHECK (attivo IN (0, 1)),
            FOREIGN KEY(utente_id) REFERENCES utente (id) ON DELETE RESTRICT,
            FOREIGN KEY(segnalazione_id) REFERENCES segnalazione (id) ON DELETE RESTRICT
        )""",
        """CREATE TABLE cronologia_stato (
            id INTEGER NOT NULL AUTO_INCREMENT,
            segnalazione_id INTEGER NOT NULL,
            attore_id INTEGER,
            stato_precedente VARCHAR(32),
            stato_nuovo VARCHAR(32) NOT NULL,
            motivazione TEXT,
            data_evento DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(segnalazione_id) REFERENCES segnalazione (id) ON DELETE RESTRICT,
            FOREIGN KEY(attore_id) REFERENCES utente (id) ON DELETE SET NULL
        )""",
        """CREATE TABLE metadati_allegato (
            attachment_id INTEGER NOT NULL,
            latitudine_estratta FLOAT,
            longitudine_estratta FLOAT,
            data_originale_dichiarata DATETIME,
            informazioni_tecniche JSON,
            data_estrazione DATETIME NOT NULL,
            PRIMARY KEY (attachment_id),
            CONSTRAINT ck_metadati_latitudine CHECK (latitudine_estratta IS NULL OR latitudine_estratta BETWEEN -90 AND 90),
            CONSTRAINT ck_metadati_longitudine CHECK (longitudine_estratta IS NULL OR longitudine_estratta BETWEEN -180 AND 180),
            FOREIGN KEY(attachment_id) REFERENCES allegato (id) ON DELETE CASCADE
        )""",
        """CREATE TABLE versione_allegato (
            versione_id INTEGER NOT NULL,
            allegato_id INTEGER NOT NULL,
            segnalazione_id INTEGER NOT NULL,
            ordine INTEGER NOT NULL,
            PRIMARY KEY (versione_id, allegato_id),
            FOREIGN KEY(versione_id, segnalazione_id) REFERENCES versione (id, segnalazione_id) ON DELETE CASCADE,
            FOREIGN KEY(allegato_id, segnalazione_id) REFERENCES allegato (id, segnalazione_id) ON DELETE RESTRICT,
            CONSTRAINT uq_versione_allegato_ordine UNIQUE (versione_id, ordine),
            CONSTRAINT ck_versione_allegato_ordine CHECK (ordine >= 0)
        )""",
        """CREATE TABLE assegnazione_categoria (
            versione_id INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            origine VARCHAR(8) NOT NULL,
            indicazione VARCHAR(12) NOT NULL,
            confidenza FLOAT,
            data_assegnazione DATETIME NOT NULL,
            PRIMARY KEY (versione_id, categoria_id, origine),
            CONSTRAINT ck_assegnazione_origine CHECK (origine IN ('UTENTE', 'IA', 'ADMIN')),
            CONSTRAINT ck_assegnazione_indicazione CHECK (indicazione IN ('SELEZIONATA', 'SUGGERITA', 'CONFERMATA', 'ESCLUSA')),
            CONSTRAINT ck_assegnazione_coerenza CHECK ((origine = 'UTENTE' AND indicazione = 'SELEZIONATA') OR (origine = 'IA' AND indicazione = 'SUGGERITA') OR (origine = 'ADMIN' AND indicazione IN ('CONFERMATA', 'ESCLUSA'))),
            CONSTRAINT ck_assegnazione_confidenza CHECK (confidenza IS NULL OR confidenza BETWEEN 0 AND 1),
            FOREIGN KEY(versione_id) REFERENCES versione (id) ON DELETE CASCADE,
            FOREIGN KEY(categoria_id) REFERENCES categoria (id) ON DELETE RESTRICT
        )""",
        """CREATE TABLE pubblicazione (
            segnalazione_id INTEGER NOT NULL,
            versione_id INTEGER NOT NULL,
            data_pubblicazione DATETIME NOT NULL,
            PRIMARY KEY (segnalazione_id),
            FOREIGN KEY(versione_id, segnalazione_id) REFERENCES versione (id, segnalazione_id) ON DELETE RESTRICT,
            FOREIGN KEY(segnalazione_id) REFERENCES segnalazione (id) ON DELETE CASCADE,
            UNIQUE (versione_id)
        )""",
        """CREATE TABLE decisione_moderazione (
            id INTEGER NOT NULL AUTO_INCREMENT,
            versione_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            esito VARCHAR(24) NOT NULL,
            motivazione TEXT NOT NULL,
            data_decisione DATETIME NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT ck_decisione_esito CHECK (esito IN ('APPROVATA', 'RIFIUTATA', 'RICHIESTE_MODIFICHE')),
            FOREIGN KEY(versione_id) REFERENCES versione (id) ON DELETE RESTRICT,
            FOREIGN KEY(admin_id) REFERENCES utente (id) ON DELETE RESTRICT
        )""",
        "CREATE INDEX ix_segnalazione_autore ON segnalazione (autore_id)",
        "CREATE INDEX ix_log_audit_entita ON log_audit (tipo_entita, id_entita, data_evento)",
        "CREATE INDEX ix_allegato_segnalazione ON allegato (segnalazione_id)",
        "CREATE INDEX ix_sostegno_classifica ON sostegno (segnalazione_id, attivo)",
        "CREATE INDEX ix_cronologia_segnalazione ON cronologia_stato (segnalazione_id, data_evento)",
        "CREATE INDEX ix_decisione_versione ON decisione_moderazione (versione_id, data_decisione)",
    )
    for statement in statements:
        op.execute(statement)


def downgrade():
    raise RuntimeError("Downgrade distruttivo disabilitato: applicare una migrazione correttiva in avanti.")