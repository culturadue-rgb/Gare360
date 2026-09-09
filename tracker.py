"""
Tracker delle prestazioni per criterio — lo compili tu.

File: data/tracker.csv (apribile anche in Excel). Una riga per criterio:

    criterio,tipo,resa,n,note
    Progetto tecnico,qualitativo,0.70,3,"media delle ultime 3 gare"

- resa: frazione 0–1 dei punti massimi che prendete di solito su quel criterio
- n:    numero di gare su cui si basa (informativo, non usato nel calcolo)
- note: libere

Il simulatore legge la resa da qui (per nome di criterio, senza distinzione
maiuscole/spazi). Puoi modificarlo dall'app (griglia + editor testo) o a mano.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from simulator import normalizza

TRACKER_PATH = Path(__file__).parent / "data" / "tracker.csv"
COLONNE = ["criterio", "tipo", "resa", "n", "note"]


# ---------------------------------------------------------------------------
# Lettura / scrittura
# ---------------------------------------------------------------------------

def leggi_righe() -> list[dict]:
    """Righe del CSV come dict con tipi già convertiti."""
    if not TRACKER_PATH.exists():
        return []
    righe = []
    with open(TRACKER_PATH, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            nome = (r.get("criterio") or "").strip()
            if not nome:
                continue
            try:
                resa = float(str(r.get("resa", "")).replace(",", "."))
            except ValueError:
                continue
            resa = max(0.0, min(1.0, resa))
            try:
                n = int(float(str(r.get("n") or 0).replace(",", ".")))
            except ValueError:
                n = 0
            tipo = (r.get("tipo") or "qualitativo").strip().lower()
            righe.append({"criterio": nome, "tipo": "tabellare" if tipo.startswith("tab") else "qualitativo",
                          "resa": resa, "n": n, "note": (r.get("note") or "").strip()})
    return righe


def scrivi_righe(righe: list[dict]) -> None:
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNE)
        w.writeheader()
        for r in righe:
            if str(r.get("criterio", "")).strip():
                w.writerow({c: r.get(c, "") for c in COLONNE})


def leggi_testo() -> str:
    if TRACKER_PATH.exists():
        return TRACKER_PATH.read_text(encoding="utf-8")
    return ",".join(COLONNE) + "\n"


def salva_testo(testo: str) -> None:
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_PATH.write_text(testo, encoding="utf-8")


def valida_testo(testo: str) -> str | None:
    """Ritorna un messaggio d'errore se il CSV non è leggibile, altrimenti None."""
    try:
        rd = csv.DictReader(io.StringIO(testo))
        if not rd.fieldnames or "criterio" not in rd.fieldnames or "resa" not in rd.fieldnames:
            return "L'intestazione deve contenere almeno le colonne 'criterio' e 'resa'."
        for i, r in enumerate(rd, 2):
            if (r.get("criterio") or "").strip():
                float(str(r.get("resa", "")).replace(",", "."))
    except ValueError:
        return f"Riga {i}: la resa deve essere un numero fra 0 e 1."
    return None


# ---------------------------------------------------------------------------
# Struttura usata dal simulatore
# ---------------------------------------------------------------------------

def carica() -> dict:
    """{'criteri': {chiave: {nome, tipo, n, resa_media, note}}}"""
    return {"criteri": {
        normalizza(r["criterio"]): {"nome": r["criterio"], "tipo": r["tipo"], "n": r["n"],
                                    "resa_media": r["resa"], "note": r["note"]}
        for r in leggi_righe()
    }}
