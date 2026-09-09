"""
Backend FastAPI — espone come API le funzioni di simulator, tracker, archive, chatbot.

Variabili d'ambiente:
  ANTHROPIC_API_KEY  chiave per l'assistente (obbligatoria solo per /api/chat)
  STRATEGA_MODEL     modello di default (opzionale)
  ALLOWED_ORIGINS    origini CORS separate da virgola (es. https://tuo-frontend.vercel.app)
  DATA_DIR           cartella con storico-gare.md e tracker.csv (default: ./data)
  PROMPTS_DIR        cartella del prompt di sistema (default: ./prompts)

Avvio locale:  uvicorn main:app --reload
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import archive
import chatbot
import tracker as trk
from simulator import ConfigGara, Concorrente, Criterio, simula

app = FastAPI(title="Alloro API", version="1.0.0")

origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app" if os.environ.get("ALLOW_VERCEL_PREVIEWS", "1") == "1" else None,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemi
# ---------------------------------------------------------------------------

class CriterioIn(BaseModel):
    nome: str
    tipo: Literal["tabellare", "qualitativo"] = "qualitativo"
    punti_max: float = Field(ge=0)
    resa_override: Optional[float] = Field(default=None, ge=0, le=1)


class ConcorrenteIn(BaseModel):
    nome: str
    livello_tecnico: float = Field(ge=0, le=1)
    ribasso: float = Field(ge=0, le=100)


class ConfigIn(BaseModel):
    nome: str = "Nuova gara"
    base_asta: float = 0
    punti_tecnico: float = 70
    punti_economico: float = 30
    criteri: list[CriterioIn]
    formula_prezzo: Literal["lineare", "proporzionale", "bilineare"] = "lineare"
    coeff_bilineare: float = 0.85
    soglia_sbarramento: Optional[float] = None
    riparametrazione: bool = False


class SimulaIn(BaseModel):
    config: ConfigIn
    ribasso_nostro: float = Field(ge=0, le=100)
    concorrenti: list[ConcorrenteIn] = []


class RigaTracker(BaseModel):
    criterio: str
    tipo: Literal["tabellare", "qualitativo"] = "qualitativo"
    resa: float = Field(ge=0, le=1)
    n: int = 0
    note: str = ""


class TestoIn(BaseModel):
    testo: str


class RigaCriterioScheda(BaseModel):
    criterio: str
    tipo: str = "qualitativo"
    punti_max: float = 0
    punti_presi: float = 0
    note: str = ""


class SchedaIn(BaseModel):
    titolo: str
    ente: str = ""
    oggetto: str = ""
    anno: str = ""
    base_asta: Optional[float] = None
    punti_tecnico: Optional[float] = None
    punti_economico: Optional[float] = None
    soglia: str = ""
    risultato: str = ""
    punteggio_nostro: Optional[float] = None
    punteggio_vincitore: Optional[float] = None
    posizione: str = ""
    distacco: str = ""
    ribasso_nostro: Optional[float] = None
    ribasso_vincitore: Optional[float] = None
    formula_prezzo: str = ""
    criteri: list[RigaCriterioScheda] = []
    funzionato: str = ""
    persi: str = ""
    riutilizzabili: str = ""
    note_ente: str = ""


class Messaggio(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    messaggi: list[Messaggio]
    includi_contesto: bool = True
    modello: Optional[str] = None


# ---------------------------------------------------------------------------
# Salute
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"ok": True, "chiave_api_configurata": chatbot.chiave_configurata(),
            "modello_default": chatbot.MODELLO_DEFAULT}


# ---------------------------------------------------------------------------
# Simulatore
# ---------------------------------------------------------------------------

@app.post("/api/simula")
def api_simula(body: SimulaIn):
    c = body.config
    cfg = ConfigGara(
        nome=c.nome, base_asta=c.base_asta, punti_tecnico=c.punti_tecnico, punti_economico=c.punti_economico,
        criteri=[Criterio(x.nome, x.tipo, x.punti_max, x.resa_override) for x in c.criteri if x.nome.strip()],
        formula_prezzo=c.formula_prezzo, coeff_bilineare=c.coeff_bilineare,
        soglia_sbarramento=c.soglia_sbarramento, riparametrazione=c.riparametrazione,
    )
    conc = [Concorrente(x.nome, x.livello_tecnico, x.ribasso) for x in body.concorrenti if x.nome.strip()]
    res = simula(cfg, trk.carica(), body.ribasso_nostro, conc)

    def off(o):
        return {"nome": o.nome, "tecnico": o.tecnico, "economico": o.economico, "ribasso": o.ribasso,
                "escluso": o.escluso, "totale": o.totale}

    return {
        "graduatoria": [off(o) for o in res["graduatoria"]],
        "noi": {**off(res["noi"]), "dettaglio_criteri": res["noi"].dettaglio_criteri},
        "posizione": res["posizione"],
        "vincitore": res["vincitore"].nome,
        "distacco": res["distacco"],
        "sensibilita": res["sensibilita"],
        "somma_criteri": sum(x.punti_max for x in cfg.criteri),
    }


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

@app.get("/api/tracker")
def api_tracker():
    return {"righe": trk.leggi_righe()}


@app.put("/api/tracker")
def api_tracker_salva(righe: list[RigaTracker]):
    pulite = [r.model_dump() for r in righe if r.criterio.strip()]
    trk.scrivi_righe(pulite)
    return {"righe": trk.leggi_righe()}


@app.get("/api/tracker/raw")
def api_tracker_raw():
    return {"testo": trk.leggi_testo()}


@app.put("/api/tracker/raw")
def api_tracker_raw_salva(body: TestoIn):
    err = trk.valida_testo(body.testo)
    if err:
        raise HTTPException(400, err)
    trk.salva_testo(body.testo)
    return {"righe": trk.leggi_righe()}


# ---------------------------------------------------------------------------
# Archivio
# ---------------------------------------------------------------------------

@app.get("/api/archivio")
def api_archivio():
    return {"schede": archive.leggi_schede(), "testo": archive.leggi_testo()}


@app.put("/api/archivio/raw")
def api_archivio_salva(body: TestoIn):
    archive.salva_testo(body.testo)
    return {"schede": archive.leggi_schede()}


@app.post("/api/archivio/schede")
def api_archivio_aggiungi(s: SchedaIn):
    if not s.titolo.strip():
        raise HTTPException(400, "Il nome della gara è obbligatorio.")
    d = s.model_dump()
    d["criteri"] = [c for c in d["criteri"] if c["criterio"].strip()]
    for k in ("base_asta", "punti_tecnico", "punti_economico", "punteggio_nostro",
              "punteggio_vincitore", "ribasso_nostro", "ribasso_vincitore"):
        if d[k] is None:
            d[k] = ""
    archive.aggiungi_scheda(d)
    return {"schede": archive.leggi_schede()}


# ---------------------------------------------------------------------------
# Assistente
# ---------------------------------------------------------------------------

@app.get("/api/prompt")
def api_prompt():
    return {"testo": chatbot.carica_prompt()}


@app.put("/api/prompt")
def api_prompt_salva(body: TestoIn):
    chatbot.salva_prompt(body.testo)
    return {"testo": chatbot.carica_prompt()}


@app.post("/api/chat")
def api_chat(body: ChatIn):
    if not body.messaggi or body.messaggi[-1].role != "user":
        raise HTTPException(400, "L'ultimo messaggio deve essere dell'utente.")
    system = chatbot.costruisci_system(archive.leggi_testo(), trk.carica(), body.includi_contesto)
    try:
        testo = chatbot.rispondi([m.model_dump() for m in body.messaggi], system, body.modello)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Errore nella chiamata al modello: {e}") from e
    return {"risposta": testo}
