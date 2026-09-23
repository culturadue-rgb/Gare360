"""
Calendario delle scadenze.

Una voce per ogni data che conta: termine per le offerte, quesiti, sopralluogo,
seduta pubblica, più tutto quello che si aggiunge a mano.

DA DOVE ARRIVANO LE VOCI
------------------------
Quando una gara passa da "Da decidere" a "In lavorazione", le date presenti
nella sua scheda entrano qui da sole (origine "automatica"), collegate alla
gara. Tornando indietro a "Da decidere" l'app CHIEDE se toglierle: non le
cancella di testa sua, perché una data già comunicata all'ufficio potrebbe
servire comunque.

Ogni voce — automatica o no — si può correggere e cancellare. Una voce
automatica che è stata modificata a mano non viene più sovrascritta dalle
rigenerazioni successive: la correzione di una persona vale più di quella della
scheda.

DOVE VIVONO
-----------
In DATA_DIR/calendario.json. Quando il Drive sarà collegato diventeranno il
foglio "Calendario" di Gare360_Dati: le colonne sono già quelle previste
(id_evento, id_gara, tipo, data, ora, descrizione, origine).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import scheda as mod_scheda

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))
FILE = DATA_DIR / "calendario.json"

TIPI = ["termine offerte", "quesiti", "sopralluogo", "seduta pubblica", "altro"]
COLONNE = ["id_evento", "id_gara", "tipo", "data", "ora", "descrizione", "origine"]


class ErroreCalendario(Exception):
    """Dato non valido, con messaggio già pronto per l'utente."""


# --------------------------------------------------------------------------- #
#  Lettura e scrittura                                                         #
# --------------------------------------------------------------------------- #

def _leggi() -> list[dict]:
    if not FILE.exists():
        return []
    try:
        dati = json.loads(FILE.read_text(encoding="utf-8"))
        return dati if isinstance(dati, list) else []
    except json.JSONDecodeError:
        # Un file rovinato non deve far sparire l'app: si riparte da vuoto e la
        # copia illeggibile resta lì accanto per poterla guardare.
        FILE.replace(FILE.with_suffix(".json.rotto"))
        return []


def _scrivi(voci: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(voci, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
#  Validazione                                                                 #
# --------------------------------------------------------------------------- #

def _data_valida(valore: str) -> str:
    """Accetta AAAA-MM-GG e GG/MM/AAAA, restituisce sempre AAAA-MM-GG."""
    testo = (valore or "").strip()
    if not testo:
        raise ErroreCalendario("La data è obbligatoria.")
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", testo)
    if m:
        g, mm, a = (int(x) for x in m.groups())
        testo = f"{a:04d}-{mm:02d}-{g:02d}"
    try:
        datetime.strptime(testo, "%Y-%m-%d")
    except ValueError:
        raise ErroreCalendario(
            f"«{valore}» non è una data valida. Scrivila come 31/12/2026 oppure 2026-12-31."
        ) from None
    return testo


def _ora_valida(valore: str) -> str:
    testo = (valore or "").strip().replace(".", ":")
    if not testo:
        return ""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", testo)
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise ErroreCalendario(f"«{valore}» non è un orario valido. Scrivilo come 12:00.")
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def _normalizza(voce: dict) -> dict:
    tipo = (voce.get("tipo") or "altro").strip().lower()
    return {
        "id_evento": voce.get("id_evento") or uuid.uuid4().hex[:10],
        "id_gara": (voce.get("id_gara") or "").strip(),
        "tipo": tipo if tipo in TIPI else "altro",
        "data": _data_valida(voce.get("data", "")),
        "ora": _ora_valida(voce.get("ora", "")),
        "descrizione": (voce.get("descrizione") or "").strip(),
        "origine": "automatica" if voce.get("origine") == "automatica" else "manuale",
    }


# --------------------------------------------------------------------------- #
#  Operazioni                                                                  #
# --------------------------------------------------------------------------- #

def elenco(id_gara: Optional[str] = None, mese: Optional[str] = None,
           giorni: Optional[int] = None, giorni_indietro: int = 60) -> list[dict]:
    """
    Voci ordinate per data e ora. `mese` è "AAAA-MM".

    `giorni` limita a quelle entro N giorni in avanti, ma tiene anche quelle già
    passate degli ultimi `giorni_indietro`: una scadenza scaduta è la cosa più
    urgente da vedere, non la prima da nascondere.
    """
    voci = _leggi()
    if id_gara:
        voci = [v for v in voci if v.get("id_gara") == id_gara]
    if mese:
        voci = [v for v in voci if str(v.get("data", "")).startswith(mese)]
    if giorni is not None:
        oggi = date.today()
        dentro = []
        for v in voci:
            try:
                d = datetime.strptime(v["data"], "%Y-%m-%d").date()
            except (ValueError, KeyError):
                continue
            scarto = (d - oggi).days
            if -giorni_indietro <= scarto <= giorni:
                dentro.append(v)
        voci = dentro
    return sorted(voci, key=lambda v: (v.get("data", ""), v.get("ora", "") or "99:99"))


def aggiungi(voce: dict) -> dict:
    nuova = _normalizza(voce)
    voci = _leggi()
    voci.append(nuova)
    _scrivi(voci)
    return nuova


def aggiorna(id_evento: str, campi: dict) -> dict:
    """Modifica data, ora, descrizione o tipo di una voce."""
    voci = _leggi()
    for i, v in enumerate(voci):
        if v.get("id_evento") == id_evento:
            unita = {**v, **{k: campi[k] for k in ("tipo", "data", "ora", "descrizione")
                             if k in campi}}
            # Toccata da una persona: le rigenerazioni automatiche non la
            # sovrascriveranno più.
            unita["origine"] = "manuale"
            voci[i] = _normalizza(unita)
            _scrivi(voci)
            return voci[i]
    raise ErroreCalendario("Voce di calendario non trovata: forse è già stata cancellata.")


def elimina(id_evento: str) -> None:
    voci = _leggi()
    restanti = [v for v in voci if v.get("id_evento") != id_evento]
    if len(restanti) == len(voci):
        raise ErroreCalendario("Voce di calendario non trovata: forse è già stata cancellata.")
    _scrivi(restanti)


def elimina_di_gara(id_gara: str) -> int:
    """Toglie tutte le voci di una gara. Restituisce quante ne ha tolte."""
    voci = _leggi()
    restanti = [v for v in voci if v.get("id_gara") != id_gara]
    tolte = len(voci) - len(restanti)
    if tolte:
        _scrivi(restanti)
    return tolte


# --------------------------------------------------------------------------- #
#  Generazione dalle date della scheda                                         #
# --------------------------------------------------------------------------- #

# Quali campi della scheda diventano voci di calendario: lo dice la scheda
# stessa, con la chiave "calendario". Così aggiungere una data al modulo la
# porta nel calendario senza toccare questo file.
def _campi_con_data() -> list[tuple[str, str]]:
    return [(c["id"], c["calendario"]) for c in mod_scheda.campi_piatti() if c.get("calendario")]


def genera_da_gara(g: dict) -> dict:
    """
    Crea le voci per una gara a partire dalla sua scheda.

    Non tocca le voci che qualcuno ha già corretto a mano, e non crea doppioni:
    per ogni tipo di scadenza esiste al massimo una voce automatica.
    """
    id_gara = g["id"]
    sched = g.get("scheda") or {}
    titolo = g.get("titolo") or "gara senza nome"
    ora_offerte = (sched.get("ora_scadenza_offerte") or "").strip()

    voci = _leggi()
    per_tipo = {v["tipo"]: v for v in voci
                if v.get("id_gara") == id_gara and v.get("origine") == "automatica"}
    manuali = {v["tipo"] for v in voci
               if v.get("id_gara") == id_gara and v.get("origine") == "manuale"}

    create, aggiornate, saltate = [], [], []
    for campo, tipo in _campi_con_data():
        valore = (sched.get(campo) or "").strip()
        if not valore:
            continue
        if tipo in manuali:
            # Qualcuno l'ha già sistemata a mano: si lascia stare.
            saltate.append(tipo)
            continue
        try:
            data = _data_valida(valore)
        except ErroreCalendario:
            saltate.append(f"{tipo} (data illeggibile: «{valore}»)")
            continue

        nuova = {
            "id_gara": id_gara, "tipo": tipo, "data": data,
            "ora": ora_offerte if tipo == "termine offerte" else "",
            "descrizione": f"{tipo.capitalize()} — {titolo}",
            "origine": "automatica",
        }
        esistente = per_tipo.get(tipo)
        if esistente:
            if esistente["data"] != data or esistente["ora"] != nuova["ora"]:
                esistente.update({"data": data, "ora": nuova["ora"]})
                aggiornate.append(tipo)
        else:
            try:
                voci.append(_normalizza(nuova))
                create.append(tipo)
            except ErroreCalendario:
                saltate.append(tipo)

    _scrivi(voci)
    return {"create": create, "aggiornate": aggiornate, "saltate": saltate,
            "totale_gara": len([v for v in voci if v.get("id_gara") == id_gara])}


def conta_di_gara(id_gara: str) -> int:
    return len([v for v in _leggi() if v.get("id_gara") == id_gara])


# --------------------------------------------------------------------------- #
#  Vista per l'app                                                             #
# --------------------------------------------------------------------------- #

def giorni_mancanti(data: str) -> Optional[int]:
    try:
        return (datetime.strptime(data, "%Y-%m-%d").date() - date.today()).days
    except (ValueError, TypeError):
        return None


def urgenza(data: str) -> str:
    gg = giorni_mancanti(data)
    if gg is None:
        return "nessuna"
    if gg < 0:
        return "scaduta"
    if gg <= 3:
        return "alta"
    if gg <= 7:
        return "media"
    return "bassa"


def vista(mese: Optional[str] = None, giorni: Optional[int] = 30,
          titoli_gare: Optional[dict[str, str]] = None, giorni_indietro: int = 60) -> dict:
    """Voci arricchite con urgenza e titolo della gara, pronte da mostrare."""
    voci = elenco(mese=mese, giorni=None if mese else giorni, giorni_indietro=giorni_indietro)
    titoli = titoli_gare or {}
    fuori = []
    for v in voci:
        fuori.append({**v,
                      "giorni_mancanti": giorni_mancanti(v["data"]),
                      "urgenza": urgenza(v["data"]),
                      "titolo_gara": titoli.get(v.get("id_gara", ""), "")})
    return {"voci": fuori, "tipi": TIPI, "mese": mese, "giorni": giorni}
