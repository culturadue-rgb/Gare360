# Gare360

Strumento per decidere sulle gare d'appalto dei settori Cultura, Sociale e Servizi
educativi: raccoglie la scheda di rilevazione, tiene il calendario delle scadenze, simula il
punteggio sui dati delle gare già fatte e archivia ogni gara conclusa per rendere più
precisa la prossima.

---

## Come funziona, in breve

Una gara attraversa quattro passi, e il menu a sinistra segue lo stesso ordine:

```
Da decidere  →  In lavorazione  →  Conclusa  →  Archiviata
```

1. **Da decidere** — si compila la *scheda di rilevazione* (a mano, oppure caricando bando o
   disciplinare e lasciando che l'AI proponga i campi, che poi si correggono).
2. **In lavorazione** — le date della scheda entrano nel calendario da sole. Si caricano i
   documenti, si chiede all'assistente, si simula il punteggio.
3. **Conclusa** — l'offerta è stata presentata.
4. **Archiviata** — si compila il modulo delle 34 colonne e la gara entra nell'archivio
   storico, diventando parte della memoria su cui il simulatore ragionerà dopo.

L'ultimo passo è quello che conta: **il simulatore è preciso quanto è pieno l'archivio.**

---

## Dove stanno i dati

| Cosa | Dove |
|---|---|
| Archivio storico (34 colonne × 3 archivi) | file Excel, caricato dall'app |
| Gare in lavorazione, documenti, analisi | `DATA_DIR/gare/<id>/` |
| Calendario | `DATA_DIR/calendario.json` |
| Documenti CCNL e testo estratto | `DATA_DIR/ccnl/` |

> ⚠️ **Sul piano gratuito di Render il disco si svuota a ogni riavvio.**
> Finché i dati non stanno su Google Drive, l'unica copia che sopravvive con certezza è
> quella che scarichi da **Impostazioni → Esporta gli archivi in Excel**. Scaricala spesso.

### Passare a Google Drive

Il codice è già pronto (`backend/drive.py` e `archivio.FonteDrive`). Per accenderlo servono
tre variabili d'ambiente su Render — `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`GOOGLE_REFRESH_TOKEN` — più `GARE360_ARCHIVIO_ID` con l'id del foglio. Da quel momento
l'app legge e scrive lì, e le correzioni fatte a mano nel foglio si vedono nell'app.

**Rinnovare l'accesso a Google.** Se l'app dice *«accesso a Google scaduto, rinnovalo»*, il
refresh token non vale più: è stato revocato, la password dell'account è cambiata, oppure la
schermata di consenso su Google Cloud è rimasta in stato "Test" invece che "In produzione"
(in quel caso scade ogni 7 giorni). Si rifà così:

1. **console.cloud.google.com** → progetto Gare360 → *API e servizi* → *Schermata consenso
   OAuth*: deve risultare **In produzione**. Se non lo è, premi **Pubblica app**.
2. **developers.google.com/oauthplayground** → ingranaggio ⚙ → *Use your own OAuth
   credentials* → incolla ID client e secret → *Access type*: **Offline**.
3. Nella casella *Input your own scopes* incolla:
   `https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets`
4. *Authorize APIs* → autorizza (la schermata "app non verificata" è normale: l'app è la
   tua) → *Exchange authorization code for tokens*.
5. Copia il **Refresh token** e sostituisci `GOOGLE_REFRESH_TOKEN` su Render.

---

## Variabili d'ambiente

### Su Render (backend)

| Nome | Serve? | A cosa |
|---|---|---|
| `ANTHROPIC_API_KEY` | per l'AI | assistente, estrazione della scheda, analisi strategica, consultazione CCNL |
| `ALLOWED_ORIGINS` | sì | i siti autorizzati a parlare col backend: `https://gare360-ynfu.vercel.app` |
| `DATA_DIR` | sì | dove l'app scrive, es. `/var/data` |
| `STRATEGA_MODEL` | no | modello di default (`claude-opus-5`; per spendere meno: `claude-sonnet-5`) |
| `APP_PASSWORD` | no | **spenta**: impostandola, l'app chiede la password all'ingresso |
| `MOSTRA_DOCS` | no | lasciare `0`: a `1` pubblica l'elenco dei comandi dell'API |
| `ANTEPRIME_VERCEL` | no | lasciare `0`: a `1` riammette qualsiasi indirizzo `*.vercel.app` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | no | collegamento a Drive |
| `GARE360_ARCHIVIO_ID` | no | id del foglio Google dell'archivio |

### Su Vercel (frontend)

| Nome | A cosa serve |
|---|---|
| `VITE_API_URL` | facoltativa: indirizzo del backend, **senza barra finale**. Se manca, il sito usa `https://gare360.onrender.com` |

---

## Sicurezza

L'app è **aperta**: chiunque conosca l'indirizzo del backend può leggerla e modificarla. È
una scelta, per non mettere attriti all'uso quotidiano. Tre cose la rendono accettabile:

- il repository va tenuto **privato**, così l'indirizzo non gira;
- `/docs` è spento, quindi l'elenco dei comandi non è consultabile;
- solo il dominio del frontend può parlare col backend.

Per accendere la protezione basta aggiungere `APP_PASSWORD` su Render: il frontend se ne
accorge da solo e mostra la schermata di accesso. Nessun'altra modifica.

---

## Le tre regole che il codice rispetta ovunque

**1. Ogni dato estratto in automatico è correggibile a mano**, prima e dopo il salvataggio.
Quello che l'AI non trova resta vuoto: non viene indovinato.

**2. Ogni scheda si può cancellare**, sempre con una conferma esplicita.

**3. I numeri li calcola il codice, non l'AI.** Il simulatore è deterministico: stessi
ingressi, stesso risultato. L'AI commenta quei numeri, non li rifà. Se la formula del
disciplinare non è fra quelle calcolabili, il simulatore lo dice e mostra il testo
originale invece di approssimare — perché un punteggio economico sbagliato porta a
consigliare il ribasso sbagliato.

Lo stesso vale per la consultazione dei CCNL: si risponde solo con i passaggi trovati nei
documenti caricati, con documento e pagina, e **il codice verifica** che ogni citazione
corrisponda davvero a un passaggio fornito. Le citazioni inventate vengono marcate.

---

## Struttura

```
gare360/
├── backend/               FastAPI
│   ├── main.py            le rotte
│   ├── scheda.py          i 41 campi della scheda di rilevazione (fonte unica)
│   ├── gare.py            le gare in lavorazione, i quattro stati, le analisi salvate
│   ├── calendario.py      le scadenze
│   ├── archivio.py        i tre archivi storici, 34 colonne, Excel o Drive
│   ├── storico.py         le stime per il simulatore, ricavate dagli archivi
│   ├── simulator.py       il calcolo del punteggio (deterministico)
│   ├── ccnl.py            i contratti collettivi e la ricerca con citazioni
│   ├── drive.py           Google Drive e Fogli (pronto, non ancora attivo)
│   ├── chatbot.py         le chiamate al modello
│   └── prompts/           le istruzioni dell'assistente
├── frontend/              React + Vite
│   └── src/components/    un componente per sezione
├── render.yaml            deploy del backend
└── README.md
```

---

## API principali

| Metodo | Percorso | Cosa fa |
|---|---|---|
| GET | `/api/health` | stato del backend, della chiave AI, di Drive, della password |
| GET | `/api/scheda/campi` | definizione del modulo della scheda |
| POST | `/api/scheda/estrai` | legge un PDF e **propone** i campi, senza salvare |
| GET/POST | `/api/gare` | elenco (filtri `stato`, `settore`) e creazione |
| GET/PATCH/DELETE | `/api/gare/{id}` | scheda, aggiornamento, eliminazione |
| POST | `/api/gare/{id}/archivia` | scrive la riga in archivio e **poi** archivia la gara |
| GET | `/api/calendario` | voci del mese o dei prossimi giorni |
| POST/PATCH/DELETE | `/api/calendario[/{id}]` | aggiunta, modifica, cancellazione |
| GET | `/api/storico/stime` | resa tecnica, scarto, ribassi, concorrenti, con affidabilità |
| POST | `/api/simula/scenari` | più scenari affiancati (nessuna AI) |
| POST | `/api/gare/{id}/analisi` | analisi strategica (AI), salvata nella gara |
| GET | `/api/archivi/{nome}` | righe di un archivio, con ricerca e filtri |
| POST | `/api/archivi-importa` · GET `/api/archivi-esporta` | carica e scarica l'Excel |
| POST | `/api/ccnl/{contratto}/documenti` | carica un PDF e ne estrae il testo per pagina |
| POST | `/api/ccnl/chiedi` | consultazione con citazioni verificate |

---

## Formule di prezzo riconosciute dal simulatore

- **Lineare / proporzionale**: P = Pmax × R / Rmax
- **Bilineare** (X = 0,80 / 0,85 / 0,90): soglia = X × media dei ribassi; sotto soglia
  proporzionale, sopra interpolazione fino a Pmax.

Ogni altra formula **non viene approssimata**: il simulatore lo segnala e mostra il testo
del disciplinare. Per aggiungerne una, `backend/simulator.py`, funzione
`punteggio_economico`.

Sono gestite anche le gare a **sola offerta tecnica** (punti prezzo = 0).

---

## Sviluppo locale

```bash
# backend (porta 8000)
cd backend
pip install -r requirements.txt
cp env.example .env          # inserisci ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)
uvicorn main:app --reload

# frontend (porta 5173, con proxy /api verso localhost:8000)
cd frontend
npm install
npm run dev
```

In sviluppo lascia `VITE_API_URL` vuoto: Vite gira le richieste al backend locale.
