"""
Backend FastAPI — espone come API le funzioni di simulator, archivio, archive, chatbot.

Variabili d'ambiente:
  ANTHROPIC_API_KEY  chiave per l'assistente (obbligatoria solo per /api/chat)
  STRATEGA_MODEL     modello di default (opzionale)
  ALLOWED_ORIGINS    origini CORS separate da virgola (es. https://tuo-frontend.vercel.app)
  DATA_DIR           cartella dei dati locali: archivio Excel, gare, documenti
  PROMPTS_DIR        cartella del prompt di sistema (default: ./prompts)

Avvio locale:  uvicorn main:app --reload
"""

from __future__ import annotations

import os
import secrets
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import archive
import archivio as arch
import chatbot
import drive
import scheda as mod_scheda
from simulator import ConfigGara, Concorrente, Criterio, simula

# La documentazione automatica (/docs) elenca tutti i comandi dell'API: in
# produzione resta spenta. Per riaccenderla in locale: MOSTRA_DOCS=1
MOSTRA_DOCS = os.environ.get("MOSTRA_DOCS", "0") == "1"

app = FastAPI(
    title="Gare360 API",
    version="1.1.0",
    docs_url="/docs" if MOSTRA_DOCS else None,
    redoc_url="/redoc" if MOSTRA_DOCS else None,
    openapi_url="/openapi.json" if MOSTRA_DOCS else None,
)

# Quali siti possono parlare con questo backend. Prima era consentito QUALSIASI
# indirizzo *.vercel.app: ora solo quelli elencati qui o in ALLOWED_ORIGINS.
ORIGINI_DEFAULT = "http://localhost:5173,https://gare360-ynfu.vercel.app"
origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", ORIGINI_DEFAULT).split(",") if o.strip()]

# Le anteprime di Vercel hanno un indirizzo diverso a ogni pubblicazione: si
# possono riammettere solo di proposito, con ANTEPRIME_VERCEL=1.
regex_anteprime = r"https://.*\.vercel\.app" if os.environ.get("ANTEPRIME_VERCEL", "0") == "1" else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=regex_anteprime,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Protezione con password condivisa
# ---------------------------------------------------------------------------
# La protezione e' FACOLTATIVA ed e' SPENTA finche' non la si accende.
#
#   APP_PASSWORD non impostata  -> app aperta, si entra senza chiedere nulla
#   APP_PASSWORD impostata      -> serve la password su tutte le rotte /api
#
# Per accenderla basta aggiungere APP_PASSWORD fra le variabili d'ambiente su
# Render: il frontend se ne accorge da solo e mostra la schermata di accesso.
# Finche' resta spenta, chiunque conosca l'indirizzo del backend puo' leggere e
# cancellare le gare: tenere privato il repository evita che l'indirizzo giri.

INTESTAZIONE_PASSWORD = "X-App-Password"
ROTTE_LIBERE = {"/api/health"}


def password_configurata() -> str:
    return os.environ.get("APP_PASSWORD", "").strip()


@app.middleware("http")
async def controlla_password(request: Request, call_next):
    percorso = request.url.path

    # Prima di ogni vera richiesta il browser ne manda una di controllo (OPTIONS)
    # che non puo' portare intestazioni personalizzate: va lasciata passare,
    # altrimenti il frontend non riesce nemmeno a presentarsi.
    if request.method == "OPTIONS" or not percorso.startswith("/api") or percorso in ROTTE_LIBERE:
        return await call_next(request)

    # Nessuna password impostata: l'app e' aperta, si passa senza controlli.
    attesa = password_configurata()
    if not attesa:
        return await call_next(request)

    ricevuta = request.headers.get(INTESTAZIONE_PASSWORD, "")
    # compare_digest evita di rivelare la password un carattere alla volta
    # misurando quanto tempo impiega il confronto.
    if not secrets.compare_digest(ricevuta, attesa):
        return JSONResponse({"detail": "Password non corretta."}, status_code=401)

    return await call_next(request)


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
            "modello_default": chatbot.MODELLO_DEFAULT,
            "password_configurata": bool(password_configurata()),
            "drive": drive.stato()}


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
    res = simula(cfg, {}, body.ribasso_nostro, conc)

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
# Archivi storici: Sociale, Cultura, Servizi educativi
# ---------------------------------------------------------------------------
# Tre archivi con le stesse 34 colonne. Ogni riga e' modificabile e
# cancellabile; la conferma prima di cancellare la chiede il frontend.

from fastapi import Body  # noqa: E402


def _archivio_valido(nome: str) -> str:
    if nome not in arch.ARCHIVI:
        raise HTTPException(404, f"Archivio «{nome}» inesistente. Validi: {', '.join(arch.ARCHIVI)}.")
    return nome


def _proteggi(fn, *a, **kw):
    """Traduce gli errori dell'archivio in risposte leggibili dall'utente."""
    try:
        return fn(*a, **kw)
    except arch.ErroreArchivio as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/archivi")
def api_archivi():
    """Elenco degli archivi, con quante gare contengono e da dove vengono letti."""
    return {"archivi": arch.ARCHIVI, "colonne": arch.COLONNE, "stato": arch.stato(),
            "esiti": arch.ESITI, "stati_gara": arch.STATI_GARA}


@app.get("/api/archivi/{nome}")
def api_archivio_righe(nome: str, testo: str = "", regione: str = "", esito: str = "", anno: str = ""):
    _archivio_valido(nome)
    righe = _proteggi(arch.cerca, nome, testo=testo, regione=regione, esito=esito, anno=anno)
    return {"archivio": nome, "colonne": arch.COLONNE, "righe": righe, "totale": len(righe)}


@app.get("/api/archivi/{nome}/filtri")
def api_archivio_filtri(nome: str):
    _archivio_valido(nome)
    return _proteggi(arch.valori_filtri, nome)


@app.post("/api/archivi/{nome}")
def api_archivio_aggiungi(nome: str, riga: dict = Body(...)):
    _archivio_valido(nome)
    return _proteggi(arch.aggiungi, nome, riga)


@app.patch("/api/archivi/{nome}/{id_gara}")
def api_archivio_aggiorna(nome: str, id_gara: str, campi: dict = Body(...)):
    _archivio_valido(nome)
    return _proteggi(arch.aggiorna, nome, id_gara, campi)


@app.delete("/api/archivi/{nome}/{id_gara}")
def api_archivio_elimina(nome: str, id_gara: str):
    _archivio_valido(nome)
    _proteggi(arch.elimina, nome, id_gara)
    return {"ok": True}


@app.get("/api/archivi-esporta")
def api_archivi_esporta():
    """Scarica tutti e tre gli archivi in un Excel: e' la copia di sicurezza."""
    from fastapi.responses import Response
    dati = _proteggi(arch.esporta_excel)
    return Response(
        dati,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Archivio_Gare360_unificato.xlsx"'},
    )


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
    system = chatbot.costruisci_system(archive.leggi_testo(), {}, body.includi_contesto)
    try:
        testo = chatbot.rispondi([m.model_dump() for m in body.messaggi], system, body.modello)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Errore nella chiamata al modello: {e}") from e
    return {"risposta": testo}


# ===========================================================================
# GARE IN LAVORAZIONE, DOCUMENTI, SCADENZE  (endpoint aggiuntivi)
# ===========================================================================

from fastapi import File, Form, UploadFile  # noqa: E402

import gare  # noqa: E402


class GaraIn(BaseModel):
    titolo: str
    ente: str = ""
    settore: str = "Altro"
    scadenza: Optional[str] = None      # ISO "YYYY-MM-DDTHH:MM"
    note: str = ""
    base_asta: Optional[float] = None
    scheda: Optional[dict] = None
    criteri: Optional[dict] = None


class GaraPatch(BaseModel):
    scheda: Optional[dict] = None
    criteri: Optional[dict] = None
    titolo: Optional[str] = None
    ente: Optional[str] = None
    settore: Optional[str] = None
    scadenza: Optional[str] = None
    stato: Optional[str] = None
    note: Optional[str] = None
    base_asta: Optional[float] = None
    dati_simulatore: Optional[dict] = None
    valutazione: Optional[str] = None


class ChatGaraIn(BaseModel):
    messaggio: str
    modello: Optional[str] = None


class ModelloIn(BaseModel):
    modello: Optional[str] = None


@app.get("/api/gare/costanti")
def api_gare_costanti():
    return {"settori": gare.SETTORI, "stati": gare.STATI, "categorie_documento": gare.CATEGORIE_DOC,
            "memoria_giorni": gare.MEMORIA_GIORNI}


@app.get("/api/gare")
def api_gare_elenco(settore: Optional[str] = None, stato: Optional[str] = None, concluse: Optional[bool] = None):
    return {"gare": gare.elenco(settore, stato, concluse)}


@app.post("/api/gare")
def api_gare_crea(body: GaraIn):
    if not body.titolo.strip():
        raise HTTPException(400, "Il titolo è obbligatorio.")
    return gare.crea(body.titolo, body.ente, body.settore, body.scadenza, body.note,
                     body.base_asta, body.scheda, body.criteri)


@app.get("/api/gare/{gid}")
def api_gara(gid: str):
    try:
        return gare.carica(gid)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")


@app.patch("/api/gare/{gid}")
def api_gara_aggiorna(gid: str, body: GaraPatch):
    try:
        return gare.aggiorna(gid, body.model_dump(exclude_unset=True))
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")


@app.delete("/api/gare/{gid}")
def api_gara_elimina(gid: str):
    gare.elimina(gid)
    return {"ok": True}


@app.post("/api/gare/{gid}/memoria/riattiva")
def api_gara_riattiva(gid: str):
    try:
        return gare.riattiva_memoria(gid)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")


# --- Documenti ---------------------------------------------------------------

@app.post("/api/gare/{gid}/documenti")
async def api_gara_documento(gid: str, file: UploadFile = File(...), categoria: str = Form("altro")):
    dati = await file.read()
    if not dati:
        raise HTTPException(400, "File vuoto.")
    try:
        return gare.aggiungi_documento(gid, file.filename or "documento", dati, categoria)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")


@app.delete("/api/gare/{gid}/documenti/{doc_id}")
def api_gara_documento_rimuovi(gid: str, doc_id: str):
    try:
        return gare.rimuovi_documento(gid, doc_id)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")


@app.get("/api/gare/{gid}/documenti/{doc_id}/testo")
def api_gara_documento_testo(gid: str, doc_id: str):
    return {"testo": gare.testo_documento(gid, doc_id)}


@app.get("/api/documenti")
def api_documenti_tutti():
    return {"documenti": gare.tutti_i_documenti()}


# --- Assistente sulla gara ------------------------------------------------------

def _system_per(g: dict) -> str:
    return chatbot.system_gara(gare.contesto_gara(g), archive.leggi_testo(), {})


@app.post("/api/gare/{gid}/chat")
def api_gara_chat(gid: str, body: ChatGaraIn):
    try:
        g = gare.carica(gid)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")
    if not body.messaggio.strip():
        raise HTTPException(400, "Messaggio vuoto.")
    storico = gare.messaggi_per_modello(g)
    messaggi = storico + [{"role": "user", "content": body.messaggio}]
    try:
        risposta = chatbot.chiama(_system_per(g), messaggi, body.modello)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Errore nella chiamata al modello: {e}") from e
    g = gare.aggiungi_messaggio(g, "user", body.messaggio)
    g = gare.aggiungi_messaggio(g, "assistant", risposta)
    return {"risposta": risposta, "gara": g}


@app.post("/api/gare/{gid}/valuta")
def api_gara_valuta(gid: str, body: ModelloIn = ModelloIn()):
    try:
        g = gare.carica(gid)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")
    if not g["documenti"]:
        raise HTTPException(400, "Carica almeno un documento prima di chiedere la valutazione.")
    try:
        testo = chatbot.chiama(_system_per(g), [{"role": "user", "content": chatbot.ISTRUZIONI_VALUTAZIONE}], body.modello, max_tokens=4000)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Errore nella chiamata al modello: {e}") from e
    g["valutazione"] = testo
    if g["stato"] == "Da valutare":
        g["stato"] = "In analisi"
    g = gare.aggiungi_messaggio(g, "user", "Valuta la gara secondo la metodologia dell'app.")
    g = gare.aggiungi_messaggio(g, "assistant", testo)
    return {"valutazione": testo, "gara": g}


@app.post("/api/gare/{gid}/estrai-info")
def api_gara_estrai_info(gid: str, body: ModelloIn = ModelloIn()):
    try:
        g = gare.carica(gid)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")
    if not g["documenti"]:
        raise HTTPException(400, "Carica almeno un documento.")
    try:
        info = chatbot.estrai_json(chatbot.ISTRUZIONI_INFO, gare.contesto_gara(g), body.modello)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Estrazione non riuscita: {e}") from e
    g["info_estratte"] = info
    # completa i campi vuoti della gara con quanto trovato
    if not g["ente"] and info.get("ente"):
        g["ente"] = info["ente"]
    if not g.get("scadenza") and info.get("scadenza_offerte"):
        g["scadenza"] = info["scadenza_offerte"]
    if not g.get("base_asta") and info.get("importo_base_asta"):
        g["base_asta"] = info["importo_base_asta"]
    if g["settore"] == "Altro" and info.get("settore") in gare.SETTORI:
        g["settore"] = info["settore"]
    gare.tocca(g)
    return {"info": info, "gara": g}


@app.post("/api/gare/{gid}/estrai-simulatore")
def api_gara_estrai_simulatore(gid: str, body: ModelloIn = ModelloIn()):
    try:
        g = gare.carica(gid)
    except KeyError:
        raise HTTPException(404, "Gara non trovata.")
    if not g["documenti"]:
        raise HTTPException(400, "Carica almeno un documento (disciplinare o criteri di valutazione).")
    try:
        dati = chatbot.estrai_json(chatbot.ISTRUZIONI_SIMULATORE, gare.contesto_gara(g), body.modello)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Estrazione non riuscita: {e}") from e
    g["dati_simulatore"] = dati
    gare.tocca(g)
    return {"dati": dati, "gara": g}


# --- Scadenze / calendario -------------------------------------------------------

@app.post("/api/archivi-importa")
async def api_archivi_importa(file: UploadFile = File(...)):
    """Carica il file Excel dell'archivio. Rifiuta il file se le colonne non tornano."""
    dati = await file.read()
    if not dati:
        raise HTTPException(400, "File vuoto.")
    try:
        conteggi = arch.importa_excel(dati)
    except arch.ErroreArchivio as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "gare_per_archivio": conteggi}


# --- Scheda di rilevazione -------------------------------------------------

@app.get("/api/scheda/campi")
def api_scheda_campi():
    """Definizione del modulo: il frontend lo costruisce da qui, non a mano."""
    return {"sezioni": mod_scheda.SEZIONI, "campi_criteri": mod_scheda.CAMPI_CRITERI,
            "colonne_criterio": mod_scheda.COLONNE_CRITERIO,
            "tipi_criterio": mod_scheda.TIPI_CRITERIO}


@app.post("/api/scheda/estrai")
async def api_scheda_estrai(file: UploadFile = File(...), modello: Optional[str] = Form(None)):
    """
    Legge bando o disciplinare e PROPONE i campi della scheda. Non salva nulla:
    la gara nasce solo quando l'utente conferma, dopo aver corretto.
    """
    dati = await file.read()
    if not dati:
        raise HTTPException(400, "File vuoto.")
    testo = gare.estrai_testo(file.filename or "documento", dati)
    if not testo.strip():
        raise HTTPException(
            400, "Dal file non si ricava testo: se è una scansione va prima riconosciuta, "
                 "oppure compila la scheda a mano.")
    if not chatbot.chiave_configurata():
        raise HTTPException(
            503, "L'assistente non è configurato (manca ANTHROPIC_API_KEY): "
                 "la scheda va compilata a mano.")
    try:
        proposta = chatbot.estrai_json(chatbot.ISTRUZIONI_SCHEDA, testo[:120_000], modello)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Estrazione non riuscita: {e}") from e

    criteri = mod_scheda.normalizza_criteri(proposta.get("criteri"))
    return {
        "titolo": str(proposta.get("titolo", "")).strip(),
        "scheda": mod_scheda.normalizza_scheda(proposta.get("scheda")),
        "criteri": criteri,
        "avvisi": mod_scheda.controlla(criteri),
        "nome_file": file.filename,
        "caratteri_letti": len(testo),
    }


@app.post("/api/criteri/controlla")
def api_criteri_controlla(criteri: dict = Body(...)):
    """Avvisi sulle incoerenze dei punteggi. Non blocca: segnala e basta."""
    norm = mod_scheda.normalizza_criteri(criteri)
    return {"avvisi": mod_scheda.controlla(norm), "somma_criteri": mod_scheda.somma_criteri(norm)}


@app.get("/api/scadenze")
def api_scadenze(giorni: int = 7, mese: Optional[str] = None):
    return gare.scadenze(giorni=giorni, mese=mese)


@app.post("/api/scadenze/estrai")
async def api_scadenze_estrai(file: UploadFile = File(...), modello: Optional[str] = Form(None)):
    """Legge un PDF/DOCX e propone i dati per il calendario. Non salva nulla."""
    dati = await file.read()
    testo = gare.estrai_testo(file.filename or "documento", dati)
    proposta = gare.estrai_scadenza_euristica(testo, file.filename or "")
    if chatbot.chiave_configurata() and testo.strip():
        try:
            ai = chatbot.estrai_json(chatbot.ISTRUZIONI_SCADENZA, testo[:80_000], modello)
            for k, v in ai.items():
                if v not in (None, "", []):
                    proposta[k] = v
            proposta["fonte"] = "ai"
        except Exception as e:  # noqa: BLE001
            proposta["avviso"] = f"Estrazione AI non riuscita, uso quella euristica: {e}"
    proposta["nome_file"] = file.filename
    proposta["caratteri_letti"] = len(testo)
    return proposta


@app.post("/api/scadenze/conferma")
def api_scadenze_conferma(body: GaraIn):
    """Crea la gara nel calendario con i dati confermati dall'utente."""
    return gare.crea(body.titolo, body.ente, body.settore, body.scadenza, body.note, body.base_asta)
