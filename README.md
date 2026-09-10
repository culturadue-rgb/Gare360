# Gare360

Dashboard operativa per la gestione e valutazione delle gare d'appalto (settori Cultura e Sociale): assistente AI al centro che lavora sui documenti di ogni gara, gare in lavorazione con stati e urgenze, scadenze per settore con calendario mensile e inserimento da PDF, simulatore deterministico del punteggio collegato alla gara, tracker delle rese, archivio storico.

## Come si usa

1. **Nuova gara** (pulsante a sinistra, o trascinando il PDF del bando nel riquadro scadenze: i dati vengono estratti e proposti per la conferma).
2. Nella scheda della gara (al centro) **carichi i documenti** — bando, disciplinare, capitolato, allegati, chiarimenti — che entrano subito nel contesto dell'assistente.
3. Chiedi all'assistente, oppure usa i pulsanti **Valuta la gara (GO / NO GO)**, **Estrai requisiti e scadenze**, **Prepara il simulatore** (estrae criteri, punteggi e formula prezzo e li carica nel simulatore a destra).
4. Cambi lo **stato** (Da valutare → In analisi → GO / NO GO → In preparazione → Presentata → Archiviata) dalla scheda.
5. La gara resta tra le **Gare in lavorazione** con la sua memoria (documenti, analisi, conversazione) per 15 giorni dall'ultima attività; dopo, la memoria viene archiviata e puoi riattivarla con un click.

I dati delle gare stanno in `DATA_DIR/gare/<id>/` (JSON + documenti + testi estratti), sullo stesso disco già usato da archivio e tracker.

```
gare360/
├── backend/     FastAPI (Python) — API per simulatore, tracker, archivio, assistente
├── frontend/    React + Vite — interfaccia
├── render.yaml  deploy del backend su Render
└── README.md
```

## Sviluppo locale

```bash
# backend (porta 8000)
cd backend
pip install -r requirements.txt
cp .env.example .env            # inserisci ANTHROPIC_API_KEY (serve solo all'assistente)
export $(grep -v '^#' .env | xargs)
uvicorn main:app --reload

# frontend (porta 5173, con proxy /api -> localhost:8000)
cd frontend
npm install
npm run dev
```

## Deploy

**Backend su Render** — importa il repo come Blueprint: `render.yaml` viene letto in automatico. Il servizio si chiama ancora `alloro-api` nel file: è solo l'identificativo interno di Render e cambiarlo creerebbe un nuovo servizio con un nuovo URL. Nella dashboard imposta:
- `ANTHROPIC_API_KEY` — la chiave; non va mai nel repo
- `ALLOWED_ORIGINS` — l'URL del frontend su Vercel, es. `https://gare360.vercel.app`

Il file monta un Disk da 1 GB su `/var/data` (`DATA_DIR`), così archivio e tracker sopravvivono ai redeploy. Al primo avvio `seed_data.py` copia i file iniziali se il disco è vuoto. Senza disco, i dati tornano allo stato del repo ad ogni deploy.

**Frontend su Vercel** — importa il repo con *Root Directory* = `frontend` (`vercel.json` fa il resto). Variabile d'ambiente:
- `VITE_API_URL` — l'URL del backend su Render, es. `https://alloro-api.onrender.com`

Le anteprime `*.vercel.app` sono ammesse dal CORS del backend per default (`ALLOW_VERCEL_PREVIEWS=1`); metti `0` per limitarti a `ALLOWED_ORIGINS`.

## API

| Metodo | Percorso | Cosa fa |
|---|---|---|
| GET | `/api/health` | stato, se la chiave API è configurata, modello di default |
| POST | `/api/simula` | `{config, ribasso_nostro, concorrenti}` → graduatoria, sensibilità, dettaglio criteri |
| GET / PUT | `/api/tracker` | righe del tracker (`criterio, tipo, resa, n, note`) |
| GET / PUT | `/api/tracker/raw` | il CSV come testo |
| GET | `/api/archivio` | schede parse + testo markdown |
| PUT | `/api/archivio/raw` | salva il markdown intero |
| POST | `/api/archivio/schede` | aggiunge una scheda |
| GET / PUT | `/api/prompt` | prompt di sistema dell'assistente |
| GET / POST | `/api/gare` | elenco (filtri `settore`, `stato`, `concluse`) / crea gara |
| GET / PATCH / DELETE | `/api/gare/{id}` | scheda gara, aggiornamento (stato, settore, scadenza…), eliminazione |
| POST | `/api/gare/{id}/documenti` | upload (multipart `file`, `categoria`); testo estratto da PDF/DOCX/TXT |
| DELETE | `/api/gare/{id}/documenti/{doc}` | rimuove un documento |
| POST | `/api/gare/{id}/chat` | domanda all'assistente con tutti i documenti e la memoria della gara |
| POST | `/api/gare/{id}/valuta` | valutazione GO/NO GO secondo la metodologia (tracker + archivio) |
| POST | `/api/gare/{id}/estrai-info` | requisiti, criticità, scadenze in JSON |
| POST | `/api/gare/{id}/estrai-simulatore` | criteri, punteggi, formula per il simulatore |
| POST | `/api/gare/{id}/memoria/riattiva` | riattiva la memoria dopo i 15 giorni |
| GET | `/api/documenti` | tutti i documenti di tutte le gare |
| GET | `/api/scadenze` | `?giorni=7` oppure `?mese=YYYY-MM`, divise per settore |
| POST | `/api/scadenze/estrai` | legge un PDF e propone titolo, ente, data/ora, settore (senza salvare) |
| POST | `/api/scadenze/conferma` | crea la gara con i dati confermati |
| POST | `/api/chat` | `{messaggi, includi_contesto, modello}` → risposta |

Documentazione interattiva su `/docs` a backend avviato.

## Variabili d'ambiente

| Dove | Nome | Note |
|---|---|---|
| backend | `ANTHROPIC_API_KEY` | obbligatoria solo per l'assistente |
| backend | `STRATEGA_MODEL` | modello di default (opzionale) |
| backend | `ALLOWED_ORIGINS` | origini CORS, separate da virgola |
| backend | `DATA_DIR`, `PROMPTS_DIR` | cartelle dati/prompt (default `./data`, `./prompts`) |
| frontend | `VITE_API_URL` | URL del backend; vuoto in sviluppo |

Nessuna chiave è scritta nel codice: l'assistente legge `ANTHROPIC_API_KEY` esclusivamente dall'ambiente del server e il frontend non la vede mai.

## Formule prezzo del simulatore
- **Lineare / proporzionale**: P = Pmax × R / Rmax
- **Bilineare** (a due rette, X = 0,80 / 0,85 / 0,90): soglia = X × media ribassi; sotto soglia proporzionale, sopra interpolazione fino a Pmax.

Altre formule: aggiungile in `backend/simulator.py`, funzione `punteggio_economico`.
