# Schema logico relazionale

Legenda: `PK` chiave primaria, `FK` chiave esterna, `UQ` vincolo univoco.
Le colonne sono nominate come nel database MySQL.

- `QUARTIERE(id PK, nome UQ, codice UQ)`
- `UTENTE(id PK, nome, cognome, email UQ, password_hash, ruolo, stato_account, data_registrazione, data_verifica_email, quartiere_id FK NULL -> QUARTIERE.id)`
- `SEGNALAZIONE(id PK, autore_id FK -> UTENTE.id, stato_operativo, data_creazione, data_ultimo_aggiornamento)`
- `VERSIONE(id PK, segnalazione_id FK -> SEGNALAZIONE.id, numero_versione, redattore_id FK -> UTENTE.id, titolo, descrizione, latitudine, longitudine, indirizzo, origine_localizzazione, quartiere_id FK NULL -> QUARTIERE.id, stato_moderazione, data_creazione, data_invio, motivo_modifica; UQ(segnalazione_id, numero_versione); UQ(id, segnalazione_id))`
- `ALLEGATO(id PK, segnalazione_id FK -> SEGNALAZIONE.id, caricatore_id FK -> UTENTE.id, tipo, tipo_contenuto, riferimento_storage UQ, dimensione, durata_secondi, checksum, stato_file, data_caricamento; UQ(id, segnalazione_id))`
- `METADATI_ALLEGATO(attachment_id PK/FK -> ALLEGATO.id, latitudine_estratta, longitudine_estratta, data_originale_dichiarata, informazioni_tecniche, data_estrazione)`
- `CATEGORIA(id PK, nome UQ, descrizione, attiva)`
- `VERSIONE_ALLEGATO(versione_id, allegato_id, segnalazione_id, ordine; PK(versione_id, allegato_id); FK(versione_id, segnalazione_id) -> VERSIONE(id, segnalazione_id); FK(allegato_id, segnalazione_id) -> ALLEGATO(id, segnalazione_id); UQ(versione_id, ordine))`
- `ASSEGNAZIONE_CATEGORIA(versione_id FK -> VERSIONE.id, categoria_id FK -> CATEGORIA.id, origine, indicazione, confidenza NULL, data_assegnazione; PK(versione_id, categoria_id, origine))`
- `SOSTEGNO(utente_id FK -> UTENTE.id, segnalazione_id FK -> SEGNALAZIONE.id, attivo, data_creazione, data_aggiornamento; PK(utente_id, segnalazione_id))`
- `PUBBLICAZIONE(segnalazione_id PK/FK -> SEGNALAZIONE.id, versione_id UQ, data_pubblicazione; FK(versione_id, segnalazione_id) -> VERSIONE(id, segnalazione_id))`
- `VERIFICA_EMAIL(id PK, utente_id FK -> UTENTE.id, token_hash UQ, data_creazione, data_scadenza, data_utilizzo NULL)`
- `SESSIONE_UTENTE(id PK, utente_id FK -> UTENTE.id, token_hash UQ, data_creazione, data_scadenza, data_revoca NULL)`
- `LOG_AUDIT(id PK, attore_id FK NULL -> UTENTE.id, azione, tipo_entita, id_entita NULL, dettagli JSON NULL, data_evento)`
- `CRONOLOGIA_STATO(id PK, segnalazione_id FK -> SEGNALAZIONE.id, attore_id FK NULL -> UTENTE.id, stato_precedente NULL, stato_nuovo, motivazione NULL, data_evento)`
- `DECISIONE_MODERAZIONE(id PK, versione_id FK -> VERSIONE.id, admin_id FK -> UTENTE.id, esito, motivazione, data_decisione)`

## Vincoli di dominio

- `UTENTE.ruolo`: `UTENTE` o `ADMIN`; stato account: `ATTIVO` o `DISATTIVATO`.
- `SEGNALAZIONE.stato_operativo` contiene gli stati operativi definiti nel
  modello dati; lo stato di moderazione vive separatamente su `VERSIONE`.
- Le coordinate dichiarate ed estratte rispettano i limiti geografici; la
  confidenza categoria, se presente, è compresa tra 0 e 1.
- `ASSEGNAZIONE_CATEGORIA` distingue origine e indicazione; per ogni coppia
  versione/categoria/origine esiste al massimo un'indicazione.
- La coppia utente/segnalazione è univoca per i sostegni; la segnalazione ha al
  massimo una pubblicazione corrente.
- I dettagli dei token sono conservati come hash; i token in chiaro non fanno
  parte dello schema.

La relazione `VERSIONE_ALLEGATO` include `segnalazione_id` nelle due FK composte:
questa ridondanza controllata assicura che la versione non riutilizzi per errore
un allegato appartenente a una segnalazione diversa.