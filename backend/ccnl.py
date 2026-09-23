"""
Archivio dei contratti collettivi, con consultazione su fonti certe.

Tre contratti: Multiservizi, Cooperative sociali, Federculture. Per ognuno si
caricano i PDF (testo contrattuale, rinnovi, tabelle retributive, accordi), e di
ognuno si registrano tipo, data di sottoscrizione e periodo di validità.

PERCHÉ IL TESTO SI TIENE PAGINA PER PAGINA
------------------------------------------
Una risposta su un CCNL vale solo se si può verificare. Quindi ogni pezzo di
testo conserva il numero di pagina da cui viene: la chat cita documento e
pagina, e mostra il passaggio originale sotto la risposta.

LE REGOLE DELLA CONSULTAZIONE
-----------------------------
1. Si risponde SOLO con il contenuto dei documenti caricati.
2. Ogni affermazione riporta documento e numero di pagina.
3. Sotto la risposta compaiono i passaggi citati, testuali.
4. Se l'informazione non c'è, la risposta è "Non presente nei documenti
   caricati", senza ipotesi.
5. Se due documenti si contraddicono (tipicamente testo base e rinnovo) si
   riportano entrambi, indicando qual è il più recente.

Il controllo delle citazioni è fatto dal codice, non chiesto per cortesia al
modello: una citazione che non corrisponde ai passaggi forniti viene scartata e
segnalata.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
CCNL_DIR = DATA_DIR / "ccnl"
INDICE = CCNL_DIR / "indice.json"

CONTRATTI = ["Multiservizi", "Cooperative sociali", "Federculture"]
TIPI_DOCUMENTO = ["testo contrattuale", "rinnovo", "tabelle retributive",
                  "accordo", "circolare", "altro"]

# Quanti passaggi si mandano al modello e quanto lunghi. Pochi e mirati: se il
# contesto si riempie di testo inutile la risposta peggiora.
MAX_PASSAGGI = 8
CARATTERI_PER_PASSAGGIO = 1800


class ErroreCCNL(Exception):
    """Problema con i documenti CCNL, con messaggio pronto per l'utente."""


# --------------------------------------------------------------------------- #
#  Indice dei documenti                                                        #
# --------------------------------------------------------------------------- #

def _leggi_indice() -> list[dict]:
    if not INDICE.exists():
        return []
    try:
        dati = json.loads(INDICE.read_text(encoding="utf-8"))
        return dati if isinstance(dati, list) else []
    except json.JSONDecodeError:
        return []


def _scrivi_indice(voci: list[dict]) -> None:
    CCNL_DIR.mkdir(parents=True, exist_ok=True)
    INDICE.write_text(json.dumps(voci, ensure_ascii=False, indent=2), encoding="utf-8")


def _cartella(contratto: str) -> Path:
    d = CCNL_DIR / re.sub(r"[^\w\- ]", "", contratto).strip().replace(" ", "_")
    d.mkdir(parents=True, exist_ok=True)
    return d


def elenco(contratto: Optional[str] = None) -> list[dict]:
    voci = _leggi_indice()
    if contratto:
        voci = [v for v in voci if v.get("ccnl") == contratto]
    # I più recenti per data di sottoscrizione in cima: nei CCNL il rinnovo
    # prevale sul testo base, e deve saltare all'occhio.
    return sorted(voci, key=lambda v: (v.get("data_sottoscrizione") or "", v.get("caricato") or ""),
                  reverse=True)


# --------------------------------------------------------------------------- #
#  Estrazione del testo, pagina per pagina                                     #
# --------------------------------------------------------------------------- #

def estrai_pagine(dati: bytes, nome: str) -> tuple[list[str], Optional[str]]:
    """
    (testo di ogni pagina, avviso). L'avviso c'è quando il PDF è una scansione
    senza testo: va detto subito, perché altrimenti il documento sembra caricato
    e invece è muto.
    """
    if not nome.lower().endswith(".pdf"):
        raise ErroreCCNL("Per ora si caricano solo PDF.")
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ErroreCCNL("Manca la libreria pypdf, necessaria a leggere i PDF.") from e

    import io
    try:
        lettore = PdfReader(io.BytesIO(dati))
        pagine = [(p.extract_text() or "").strip() for p in lettore.pages]
    except Exception as e:  # noqa: BLE001
        raise ErroreCCNL(f"Il PDF non è leggibile: {e}") from e

    con_testo = sum(1 for p in pagine if len(p) > 40)
    if not pagine:
        raise ErroreCCNL("Il PDF non ha pagine.")
    if con_testo == 0:
        return pagine, (
            f"«{nome}» è una scansione senza testo: non si può cercare dentro. "
            "Va prima passato per un riconoscimento del testo (OCR), altrimenti "
            "resta archiviato ma la consultazione non lo vedrà.")
    if con_testo < len(pagine) / 2:
        return pagine, (
            f"Solo {con_testo} pagine su {len(pagine)} di «{nome}» contengono testo: "
            "il resto è probabilmente scansionato e non sarà consultabile.")
    return pagine, None


def aggiungi_documento(contratto: str, nome: str, dati: bytes, meta: dict) -> dict:
    if contratto not in CONTRATTI:
        raise ErroreCCNL(f"Contratto «{contratto}» sconosciuto. Validi: {', '.join(CONTRATTI)}.")

    pagine, avviso = estrai_pagine(dati, nome)
    id_doc = uuid.uuid4().hex[:10]
    cartella = _cartella(contratto)
    (cartella / f"{id_doc}.pdf").write_bytes(dati)
    (cartella / f"{id_doc}_pagine.json").write_text(
        json.dumps({"nome": nome, "pagine": pagine}, ensure_ascii=False), encoding="utf-8")

    tipo = (meta.get("tipo_documento") or "altro").strip().lower()
    voce = {
        "id_documento": id_doc,
        "ccnl": contratto,
        "tipo_documento": tipo if tipo in TIPI_DOCUMENTO else "altro",
        "data_sottoscrizione": (meta.get("data_sottoscrizione") or "").strip(),
        "validita_da": (meta.get("validita_da") or "").strip(),
        "validita_a": (meta.get("validita_a") or "").strip(),
        "nome_file": nome,
        "numero_pagine": len(pagine),
        "pagine_con_testo": sum(1 for p in pagine if len(p) > 40),
        "caricato": datetime.now().replace(microsecond=0).isoformat(),
        "avviso": avviso,
    }
    voci = _leggi_indice()
    voci.append(voce)
    _scrivi_indice(voci)
    return voce


def elimina_documento(id_doc: str) -> None:
    voci = _leggi_indice()
    voce = next((v for v in voci if v.get("id_documento") == id_doc), None)
    if not voce:
        raise ErroreCCNL("Documento non trovato: forse è già stato eliminato.")
    cartella = _cartella(voce["ccnl"])
    for f in (cartella / f"{id_doc}.pdf", cartella / f"{id_doc}_pagine.json"):
        f.unlink(missing_ok=True)
    _scrivi_indice([v for v in voci if v.get("id_documento") != id_doc])


def aggiorna_documento(id_doc: str, campi: dict) -> dict:
    voci = _leggi_indice()
    for i, v in enumerate(voci):
        if v.get("id_documento") == id_doc:
            for k in ("tipo_documento", "data_sottoscrizione", "validita_da", "validita_a"):
                if k in campi:
                    v[k] = (campi[k] or "").strip()
            voci[i] = v
            _scrivi_indice(voci)
            return v
    raise ErroreCCNL("Documento non trovato.")


def _pagine_di(voce: dict) -> list[str]:
    f = _cartella(voce["ccnl"]) / f"{voce['id_documento']}_pagine.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("pagine", [])
    except json.JSONDecodeError:
        return []


# --------------------------------------------------------------------------- #
#  Ricerca dei passaggi pertinenti                                             #
# --------------------------------------------------------------------------- #

_ACCENTI = str.maketrans("àèéìíîòóùúÀÈÉÌÍÎÒÓÙÚ", "aeeiiioouuAEEIIIOOUU")

# Parole troppo comuni per selezionare qualcosa.
VUOTE = {"come", "dove", "quale", "quali", "quanto", "quanti", "essere", "avere",
         "della", "dello", "delle", "degli", "nella", "nelle", "questo", "questa",
         "sono", "viene", "vengono", "deve", "devono", "puo", "possono", "anche",
         "per", "con", "che", "non", "una", "uno", "del", "dei", "nel", "sul"}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").translate(_ACCENTI)).lower()


def _parole(testo: str) -> list[str]:
    return [p for p in re.findall(r"[a-z0-9]{3,}", _norm(testo)) if p not in VUOTE]


def cerca_passaggi(domanda: str, contratto: Optional[str] = None,
                   massimo: int = MAX_PASSAGGI) -> list[dict]:
    """
    I passaggi più pertinenti, uno per pagina, con il riferimento completo.

    Il punteggio è semplice e trasparente: quante parole della domanda compaiono
    nella pagina, quante volte. Niente di sofisticato, ma verificabile — e ogni
    passaggio resta legato al suo documento e alla sua pagina.
    """
    parole = _parole(domanda)
    if not parole:
        return []

    trovati = []
    for voce in elenco(contratto):
        pagine = _pagine_di(voce)
        for n_pagina, testo in enumerate(pagine, start=1):
            if len(testo) < 40:
                continue
            piatto = _norm(testo)
            punti = sum(piatto.count(p) for p in parole)
            distinte = sum(1 for p in parole if p in piatto)
            if not distinte:
                continue
            # Le parole distinte contano più delle ripetizioni: una pagina che
            # tocca tutti i termini della domanda è più utile di una che ripete
            # dieci volte lo stesso.
            trovati.append({
                "id_documento": voce["id_documento"],
                "ccnl": voce["ccnl"],
                "documento": voce["nome_file"],
                "tipo_documento": voce["tipo_documento"],
                "data_sottoscrizione": voce.get("data_sottoscrizione", ""),
                "pagina": n_pagina,
                "punteggio": distinte * 10 + punti,
                "testo": testo[:CARATTERI_PER_PASSAGGIO],
            })

    trovati.sort(key=lambda t: (-t["punteggio"], t["documento"], t["pagina"]))
    return trovati[:massimo]


# --------------------------------------------------------------------------- #
#  Controllo delle citazioni                                                   #
# --------------------------------------------------------------------------- #

_RE_CITAZIONE = re.compile(r"\(([^()]*?)\bp(?:ag(?:ina)?)?\.?\s*(\d{1,4})\s*\)", re.IGNORECASE)


def verifica_citazioni(risposta: str, passaggi: list[dict]) -> tuple[str, list[str]]:
    """
    Controlla che ogni «(documento, p. N)» corrisponda a un passaggio realmente
    fornito. Le citazioni inventate vengono marcate nel testo e segnalate.

    È il codice a controllare, non il modello a promettere.
    """
    ammesse = {(p["documento"].lower(), p["pagina"]) for p in passaggi}
    pagine_ammesse = {p["pagina"] for p in passaggi}
    problemi: list[str] = []

    def sostituisci(m):
        testo_doc, pagina = m.group(1).strip(" ,;"), int(m.group(2))
        buona = any(pagina == pag and (testo_doc.lower() in doc or doc in testo_doc.lower())
                    for doc, pag in ammesse)
        if buona or (not testo_doc and pagina in pagine_ammesse):
            return m.group(0)
        problemi.append(f"«{m.group(0)}» non corrisponde a nessun passaggio fornito")
        return m.group(0) + " ⚠️"

    corretta = _RE_CITAZIONE.sub(sostituisci, risposta)
    return corretta, problemi


def istruzioni(passaggi: list[dict]) -> str:
    """Il prompt della consultazione: le regole, più i soli passaggi trovati."""
    if not passaggi:
        return (
            "Nei documenti caricati non è stato trovato alcun passaggio pertinente.\n"
            "Rispondi esattamente: «Non presente nei documenti caricati.» e nient'altro."
        )

    blocchi = []
    for i, p in enumerate(passaggi, 1):
        data = f", sottoscritto il {p['data_sottoscrizione']}" if p["data_sottoscrizione"] else ""
        blocchi.append(
            f"[{i}] {p['documento']} — {p['ccnl']}, {p['tipo_documento']}{data} — pagina {p['pagina']}\n"
            f"{p['testo']}"
        )

    return f"""Rispondi alla domanda usando ESCLUSIVAMENTE i passaggi qui sotto.

REGOLE, senza eccezioni:
1. Non usare conoscenze generali sui CCNL. Solo questi passaggi.
2. Ogni affermazione porta il riferimento fra parentesi: (nome del file, p. numero).
   Usa i numeri di pagina esattamente come compaiono qui sotto.
3. Se la risposta non è in questi passaggi, scrivi esattamente:
   «Non presente nei documenti caricati.» e fermati.
4. Se due passaggi si contraddicono, riportali entrambi e indica quale documento
   è più recente in base alla data di sottoscrizione.
5. Niente premesse e niente riepiloghi: la risposta e i riferimenti.

PASSAGGI DISPONIBILI

{chr(10).join(blocchi)}
"""
