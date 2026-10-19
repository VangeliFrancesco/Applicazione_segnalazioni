# La Nostra Città, Il Nostro Futuro

Piattaforma civica del comitato **Insieme per Milano** per raccogliere e
ordinare segnalazioni urbane documentate. Non è un portale ufficiale del Comune:
la presa in carico è del comitato e l'invio ai candidati non equivale alla
risoluzione del problema.

## Avvio nel Codespace

Il container installa le dipendenze definite in `pyproject.toml`. Configura i
Codespaces Secrets richiesti in `.env.example` (o un `.env` locale ignorato da
Git), includendo il certificato CA Aiven nel percorso indicato da
`DB_SSL_CA`. La connessione rifiuta modalità TLS diverse da
`VERIFY_IDENTITY` e verifica certificato e hostname.

Avvio previsto dopo la configurazione dei secrets:

```bash
python -m flask --app app:create_app run --host=0.0.0.0 --port=5000
```

La porta 5000 viene inoltrata come privata. Non usare il debugger interattivo su
una porta pubblica. Il database configurato in `DB_NAME` è
`applicazione_segnalazioni`; la revisione Alembic `0002_seed_default_categories`
è stata applicata. Prima di collegare un altro database, verificarne versione,
tabelle e dati esistenti.

Per visualizzare soltanto l'interfaccia senza configurare Aiven, avvia la
modalità preview:

```bash
PREVIEW_MODE=1 python -m flask --app app:create_app run --host=0.0.0.0 --port=5000
```

Questa modalità usa un database SQLite in memoria separato da MySQL, con un
account utente, un account admin e una segnalazione dimostrativa. Puoi provare
registrazione, accesso, invio e moderazione; i dati temporanei si perdono al
riavvio. Le credenziali demo sono mostrate nella home. Google Fonts e le mappe
OpenStreetMap richiedono una connessione Internet nel browser.

## Modello e perimetro

- [Requisiti e perimetro](docs/requisiti.md)
- [Modello dati e architettura](docs/modello-dati.md)
- [Schema logico relazionale](docs/schema-logico.md)
- [DDL per MySQL](docs/schema-mysql.sql)
- [Schema DBML](docs/schema.dbml)

La piattaforma implementa registrazione e accesso, ruoli utente/amministratore,
creazione di segnalazioni con upload obbligatorio di foto o video, posizione,
categoria e supporto da parte di altri utenti. Gli allegati sono conservati in
`instance/uploads` (modificabile con `UPLOAD_FOLDER`), hanno un limite di 64 MB
e sono accessibili solo agli amministratori durante la moderazione. Gli eventi
di autenticazione, invio, supporto e moderazione sono registrati nell'audit log;
le transizioni di stato sono limitate e archiviate nella cronologia.

La registrazione pubblica assegna sempre il ruolo `UTENTE`. Dopo aver
configurato il database, crea un amministratore iniziale con:

```bash
flask --app app:create_app create-admin
```

Il comando richiede i dati interattivamente e non espone l'assegnazione del
ruolo amministrativo nella registrazione web.

## Verifiche locali

```bash
python -m pytest
```

I test di schema non richiedono credenziali né connessione MySQL. I test di
integrazione MySQL saranno separati e richiederanno un database di test dedicato.