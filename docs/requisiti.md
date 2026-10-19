# Requisiti e perimetro

## Obiettivo

Raccogliere segnalazioni e priorità urbane documentate per il comitato di
cittadini Insieme per Milano. La piattaforma è indipendente dal Comune: la presa
in carico indica l'attività del comitato; l'invio ai candidati non indica che il
problema sia stato risolto.

## Perimetro dati approvato

Il modello contiene utenti con ruolo e stato, quartieri, segnalazioni e versioni,
allegati con metadati separati, categorie, assegnazioni di categoria, sostegni
univoci per utente/segnalazione e una sola pubblicazione corrente per
segnalazione. Ogni decisione di moderazione è associata alla versione esaminata.

Le estensioni approvate sono verifica email con token conservato come hash e
scadenza, sessioni revocabili, audit delle azioni e cronologia degli stati.

Politiche confermate: consultazione pubblica prevista; quartiere di residenza
facoltativo; niente autosostegno; un admin non modera una propria segnalazione.
Le segnalazioni inviate richiedono approvazione admin per la pubblicazione.
Rifiuto e attesa chiarimenti non sono pubblici. Le modifiche successive
producono una nuova versione. Il contenuto multimediale richiesto è almeno una
foto oppure un video, non entrambi obbligatoriamente.

## Esclusioni di questa fase

Non sono inclusi moduli IA, gestione strutturata dei chiarimenti, selezione
programmatica, consegna automatica ai candidati, invio email reale, esportazione
PDF o storage persistente esterno. La `.venv` locale è solo ambiente di
sviluppo; gli upload sono serviti da route applicative e non da `static`.

## Vincoli e responsabilità

Ruoli, transizioni consentite, account attivo, pubblicazione solo di versioni
approvate e requisito di almeno una categoria e un allegato valido sono
controllati dal backend. Un admin non può moderare una propria segnalazione. I
`CHECK` SQL rafforzano i domini di valori, ma non sostituiscono tali controlli.

La creazione della prima versione deve avvenire nella stessa transazione della
segnalazione. Una pubblicazione deve puntare a una versione della medesima
segnalazione; l'applicazione verifica che tale versione sia approvata. Il
vincolo composito nel database impedisce riferimenti incrociati.

## Stato di realizzazione

Sono implementati registrazione e accesso, ruoli utente/admin, audit, creazione
di segnalazioni con localizzazione, categoria e upload foto/video, sostegno,
moderazione, pubblicazione e transizioni di stato con cronologia. Gli allegati
sono conservati in storage locale; i media delle versioni pubblicate sono
visibili nella home. La connessione MySQL è stata verificata e lo schema atteso
è presente; il database è attualmente privo di dati applicativi. Invio email
reale, verifica email interattiva, storage persistente esterno, chiarimenti
strutturati, consegna automatica ai candidati, IA e PDF restano esclusi.