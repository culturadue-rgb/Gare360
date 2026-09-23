"""
Stime storiche per il simulatore, ricavate dagli archivi.

Prende il posto del vecchio tracker: le rese non si dichiarano più a mano, si
calcolano dalle gare realmente fatte.

COSA CALCOLA
------------
  resa_tecnica      punteggio_tecnico / max_punteggio_tecnico, in percentuale.
                    Il rapporto, non il punteggio assoluto: così una gara su 70
                    punti e una su 100 diventano confrontabili.
  livello_rivali    scarto_tecnico, cioè quanto il vincitore ci ha staccati sul
                    tecnico. Dice contro chi si gioca.
  ribassi           nostro_ribasso: cosa abbiamo offerto, e con quale esito.
  concorrenti       quanti si presentano di solito, e con che punteggi ha vinto
                    chi ha vinto.

REGOLE, VOLUTAMENTE PRUDENTI
----------------------------
- Si usano le gare dello stesso archivio. Se ce ne sono almeno CAMPIONE_MINIMO
  con il dato, si usano SOLO quelle; sotto quella soglia si allarga a tutti gli
  archivi, dicendolo.
- Le righe senza il dato vengono escluse, non contate come zero.
- Ogni stima dichiara SEMPRE su quante gare si basa e quali sono, così la si può
  verificare e si possono escludere le gare che non c'entrano.
- Con pochi dati l'affidabilità è dichiarata bassa. Una media su due gare non è
  una previsione: è un indizio.
"""

from __future__ import annotations

import statistics
from typing import Any, Optional

import archivio

CAMPIONE_MINIMO = 5          # sotto questa soglia si allarga agli altri archivi
CAMPIONE_AFFIDABILE = 8      # da qui in su l'affidabilità sale a "media"


def _num(riga: dict, colonna: str) -> Optional[float]:
    return archivio.numero(riga.get(colonna))


def _affidabilita(n: int) -> str:
    if n >= CAMPIONE_AFFIDABILE:
        return "media"
    if n >= CAMPIONE_MINIMO:
        return "bassa"
    return "molto bassa"


def _riga_sintetica(r: dict) -> dict:
    """Quel tanto che basta per riconoscere la gara e andarla a vedere."""
    return {
        "id_gara": r.get("id_gara", ""),
        "titolo": r.get("titolo_gara", "") or r.get("stazione_appaltante", ""),
        "ente": r.get("stazione_appaltante", ""),
        "esito": r.get("esito_gara", ""),
        "regione": r.get("regione", ""),
        "url_cartella": r.get("url_cartella", ""),
    }


# --------------------------------------------------------------------------- #
#  Raccolta delle righe utilizzabili                                           #
# --------------------------------------------------------------------------- #

def _righe(archivio_nome: Optional[str], escludi: set[str]) -> tuple[list[dict], list[str]]:
    """Righe dell'archivio indicato (o di tutti), meno quelle escluse a mano."""
    nomi = [archivio_nome] if archivio_nome in archivio.ARCHIVI else archivio.ARCHIVI
    righe, problemi = [], []
    for nome in nomi:
        try:
            for r in archivio.elenco(nome):
                if r.get("id_gara") in escludi:
                    continue
                righe.append({**r, "_archivio": nome})
        except archivio.ErroreArchivio as e:
            problemi.append(str(e))
    return righe, problemi


def _statistica(valori: list[float]) -> dict:
    return {
        "n": len(valori),
        "media": round(statistics.fmean(valori), 2),
        "mediana": round(statistics.median(valori), 2),
        "minimo": round(min(valori), 2),
        "massimo": round(max(valori), 2),
    }


def _stima(righe: list[dict], calcola, archivio_nome: Optional[str]) -> dict:
    """
    Applica `calcola` a ogni riga, tiene i valori validi e costruisce la stima
    con dentro l'elenco delle gare usate.

    Se nell'archivio richiesto ci sono meno di CAMPIONE_MINIMO valori, allarga a
    tutti gli archivi — e lo dichiara, invece di far finta di niente.
    """
    def raccogli(sorgente):
        usate, valori = [], []
        for r in sorgente:
            v = calcola(r)
            if v is None:
                continue
            valori.append(v)
            usate.append({**_riga_sintetica(r), "valore": round(v, 2), "archivio": r["_archivio"]})
        return valori, usate

    dentro = [r for r in righe if not archivio_nome or r["_archivio"] == archivio_nome]
    valori, usate = raccogli(dentro)
    allargata = False

    if len(valori) < CAMPIONE_MINIMO and archivio_nome:
        valori, usate = raccogli(righe)
        allargata = True

    if not valori:
        return {"disponibile": False, "n": 0, "affidabilita": "nessun dato",
                "gare_usate": [], "allargata_ad_altri_archivi": False,
                "nota": "Nessuna gara in archivio ha questo dato compilato."}

    stat = _statistica(valori)
    nota = f"Stima su {stat['n']} gare."
    if allargata:
        nota += (f" Nell'archivio «{archivio_nome}» ce n'erano meno di {CAMPIONE_MINIMO}, "
                 "quindi sono state usate anche quelle degli altri archivi.")
    if stat["n"] < CAMPIONE_MINIMO:
        nota += " Sono troppo poche per una previsione: prendila come un indizio."

    return {"disponibile": True, **stat, "affidabilita": _affidabilita(stat["n"]),
            "gare_usate": sorted(usate, key=lambda u: u["id_gara"]),
            "allargata_ad_altri_archivi": allargata, "nota": nota}


# --------------------------------------------------------------------------- #
#  Le quattro stime                                                            #
# --------------------------------------------------------------------------- #

def _resa_tecnica(r: dict) -> Optional[float]:
    nostro, massimo = _num(r, "punteggio_tecnico"), _num(r, "max_punteggio_tecnico")
    if nostro is None or not massimo:
        return None
    return nostro / massimo * 100


def _scarto(r: dict) -> Optional[float]:
    return _num(r, "scarto_tecnico")


def _ribasso(r: dict) -> Optional[float]:
    return _num(r, "nostro_ribasso")


def _concorrenti(r: dict) -> Optional[float]:
    return _num(r, "n_concorrenti")


def stime(archivio_nome: Optional[str] = None, escludi: Optional[list[str]] = None) -> dict:
    """
    Tutte le stime per un archivio. `escludi` toglie gare che non si vogliono
    contare (una gara anomala, un lotto doppio).
    """
    righe, problemi = _righe(None, set(escludi or []))

    risultato = {
        "archivio": archivio_nome,
        "resa_tecnica": _stima(righe, _resa_tecnica, archivio_nome),
        "scarto_dal_vincitore": _stima(righe, _scarto, archivio_nome),
        "nostro_ribasso": _stima(righe, _ribasso, archivio_nome),
        "n_concorrenti": _stima(righe, _concorrenti, archivio_nome),
        "escluse": sorted(escludi or []),
        "problemi": problemi,
    }

    # Esiti: quante vinte su quante con esito noto.
    dentro = [r for r in righe if not archivio_nome or r["_archivio"] == archivio_nome]
    noti = [r for r in dentro if archivio.chiave(r.get("esito_gara")) in ("vinta", "persa")]
    vinte = [r for r in noti if archivio.chiave(r.get("esito_gara")) == "vinta"]
    risultato["esiti"] = {
        "con_esito_noto": len(noti), "vinte": len(vinte),
        "tasso_vittoria": round(len(vinte) / len(noti) * 100, 1) if noti else None,
        "nota": ("Il tasso di vittoria conta solo le gare con esito registrato: "
                 "le gare in attesa e quelle non applicabili restano fuori."),
    }

    risultato["avvisi"] = avvisi(risultato)
    return risultato


def avvisi(s: dict) -> list[str]:
    """Cosa manca perché le stime diventino affidabili. Detto in chiaro."""
    fuori = []
    if not s["resa_tecnica"]["disponibile"]:
        fuori.append(
            "Nessuna gara ha insieme punteggio tecnico e punteggio massimo: senza quei due "
            "dati non si può stimare quanto prendiamo di solito sulla tecnica.")
    if not s["scarto_dal_vincitore"]["disponibile"]:
        fuori.append(
            "Nessuna gara ha lo scarto dal vincitore: il simulatore non sa contro che "
            "livello tecnico si gioca. Si compila da «punteggio tecnico del vincitore», "
            "che si trova nei verbali di commissione.")
    if not s["nostro_ribasso"]["disponibile"]:
        fuori.append(
            "Nessuna gara ha il nostro ribasso: le indicazioni di prezzo restano senza "
            "riferimento storico.")
    if s["esiti"]["con_esito_noto"] < CAMPIONE_MINIMO:
        fuori.append(
            f"Solo {s['esiti']['con_esito_noto']} gare hanno un esito registrato: troppo "
            "poche per parlare di probabilità di vittoria.")
    return fuori


def profili_concorrenti(archivio_nome: Optional[str] = None, limite: int = 12) -> list[dict]:
    """
    Le gare in cui si conosce il punteggio di chi ha vinto: sono i profili di
    concorrente più utili, perché dicono a che livello si vince davvero.
    """
    righe, _ = _righe(None, set())
    dentro = [r for r in righe if not archivio_nome or r["_archivio"] == archivio_nome]
    fuori = []
    for r in dentro:
        tec = _num(r, "punteggio_tecnico_aggiudicatario")
        massimo = _num(r, "max_punteggio_tecnico")
        if tec is None or not massimo:
            continue
        fuori.append({
            **_riga_sintetica(r),
            "tecnico_vincitore": round(tec, 2),
            "max_tecnico": round(massimo, 2),
            "livello_tecnico": round(tec / massimo, 4),
            "economico_vincitore": _num(r, "punteggio_economico_aggiudicatario"),
            "n_concorrenti": _num(r, "n_concorrenti"),
            "nostro_ribasso": _num(r, "nostro_ribasso"),
            "archivio": r["_archivio"],
        })
    return sorted(fuori, key=lambda x: -x["livello_tecnico"])[:limite]


def gare_simili(archivio_nome: str, testo: str = "", regione: str = "",
                limite: int = 8) -> list[dict]:
    """
    Precedenti confrontabili per l'analisi strategica: stessa regione e parole in
    comune nell'oggetto. Il punteggio di affinità è spiegato, non opaco.
    """
    try:
        righe = archivio.elenco(archivio_nome)
    except archivio.ErroreArchivio:
        return []

    parole = {p for p in archivio.chiave(testo).split("_") if len(p) >= 4}
    valutate = []
    for r in righe:
        punti, motivi = 0, []
        if regione and archivio.chiave(r.get("regione")) == archivio.chiave(regione):
            punti += 30
            motivi.append(f"stessa regione ({r.get('regione')})")
        comuni = parole & {p for p in archivio.chiave(r.get("titolo_gara")).split("_") if len(p) >= 4}
        if comuni:
            punti += min(len(comuni) * 8, 40)
            motivi.append("oggetto simile: " + ", ".join(sorted(comuni)))
        if _num(r, "punteggio_tecnico") is not None:
            punti += 15
            motivi.append("ha i punteggi")
        if punti:
            valutate.append({**_riga_sintetica(r), "affinita": punti, "perche": motivi,
                             "punteggio_tecnico": r.get("punteggio_tecnico"),
                             "max_punteggio_tecnico": r.get("max_punteggio_tecnico"),
                             "nostro_ribasso": r.get("nostro_ribasso"),
                             "scarto_tecnico": r.get("scarto_tecnico")})
    return sorted(valutate, key=lambda v: (-v["affinita"], v["id_gara"]))[:limite]
