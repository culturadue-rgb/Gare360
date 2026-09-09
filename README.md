# Alloro — il verbale, prima del verbale

Strumento per preparare offerte in gare d'appalto pubbliche (OEPV): simulatore deterministico del punteggio, tracker delle rese per criterio, archivio storico delle gare, assistente AI.

```
alloro/
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

**Backend su Render** — importa il repo come Blueprint: `render.yaml` viene letto in automatico. Nella dashboard imposta:
- `ANTHROPIC_API_KEY` — la chiave; non va mai nel repo
- `ALLOWED_ORIGINS` — l'URL del frontend su Vercel, es. `https://alloro.vercel.app`

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
