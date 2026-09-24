"""
Salvataggio e ripristino di tutto il contenuto dell'app.

PERCHE' SERVE
-------------
Sul piano gratuito di Render il server non ha un disco: si spegne dopo un
quarto d'ora di inattività e riparte pulito. Tutto quello che è stato caricato —
archivio, gare, calendario, contratti — sparisce. Non è un difetto dell'app: è
il server che non ha dove tenere le cose.

Finché la situazione è questa, la memoria dell'app deve stare da qualche altra
parte. Qui ci sono i due modi.

DUE LIVELLI, PER DUE ESIGENZE DIVERSE
-------------------------------------
  COMPLETO (zip)   Tutto, PDF originali compresi. È la copia da scaricare e
                   tenere da parte. Pesa quanto pesano i documenti.

  LEGGERO (json)   Tutto TRANNE i file originali caricati: restano l'archivio,
                   le gare, le schede, le analisi, il calendario, l'indice dei
                   CCNL e il TESTO già estratto dai PDF. Sta nel browser e
                   torna da solo quando il server riparte vuoto.

Il leggero tiene il testo estratto, non solo i nomi: così la consultazione dei
CCNL e il contesto delle gare continuano a funzionare senza ricaricare un
singolo PDF. Si perde la possibilità di riscaricare l'originale, non il suo
contenuto.
"""

from __future__ import annotations

import base64
import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "data"))

# I file che il salvataggio leggero porta con sé: dati e testo, non originali.
SUFFISSI_LEGGERI = {".json", ".md", ".txt", ".xlsx"}

# Un tetto al salvataggio leggero: deve stare nel browser, e un browser non è un
# disco. Oltre questa soglia si avvisa invece di fallire a metà.
LIMITE_LEGGERO = 4_000_000


class ErroreSalvataggio(Exception):
    """Messaggio già pronto per l'utente."""


def _file_presenti(solo_leggeri: bool = False) -> list[Path]:
    if not DATA_DIR.exists():
        return []
    fuori = []
    for p in sorted(DATA_DIR.rglob("*")):
        if not p.is_file():
            continue
        if solo_leggeri and p.suffix.lower() not in SUFFISSI_LEGGERI:
            continue
        fuori.append(p)
    return fuori


def vuoto() -> bool:
    """
    Il server ha perso tutto?

    Si guarda se c'è almeno un file di dati. Serve a decidere se rimettere da
    soli la copia del browser: si ripristina SOLO su un server vuoto, mai sopra
    a dati esistenti, perché sovrascrivere il lavoro di oggi con la copia di
    ieri sarebbe peggio del problema che si vuole risolvere.
    """
    return not _file_presenti()


def stato() -> dict:
    """Cosa c'è adesso sul server, in due numeri comprensibili."""
    tutti = _file_presenti()
    leggeri = _file_presenti(solo_leggeri=True)
    return {
        "vuoto": not tutti,
        "file": len(tutti),
        "byte": sum(p.stat().st_size for p in tutti),
        "byte_leggeri": sum(p.stat().st_size for p in leggeri),
        "cartella": str(DATA_DIR),
    }


# --------------------------------------------------------------------------- #
#  Completo: uno zip da scaricare                                              #
# --------------------------------------------------------------------------- #

def esporta_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for p in _file_presenti():
            z.write(p, p.relative_to(DATA_DIR).as_posix())
        z.writestr("_salvataggio.json", json.dumps({
            "versione": 1, "quando": datetime.now().replace(microsecond=0).isoformat(),
            "completo": True,
        }, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def _percorso_sicuro(nome: str) -> Path:
    """
    Dove finisce un file dello zip.

    Uno zip può contenere percorsi come "../../etc/qualcosa": estrarli così come
    sono scriverebbe fuori dalla cartella dei dati. Si tiene solo la parte
    relativa e si verifica che il risultato resti dentro DATA_DIR.
    """
    pulito = Path(nome.replace("\\", "/"))
    if pulito.is_absolute() or ".." in pulito.parts:
        raise ErroreSalvataggio(
            f"Il file di salvataggio contiene un percorso non valido: «{nome}». "
            "Non è stato ripristinato niente.")
    destinazione = (DATA_DIR / pulito).resolve()
    if not str(destinazione).startswith(str(DATA_DIR.resolve())):
        raise ErroreSalvataggio(
            f"Il file di salvataggio punta fuori dalla cartella dei dati: «{nome}». "
            "Non è stato ripristinato niente.")
    return destinazione


def importa_zip(contenuto: bytes) -> dict:
    """Rimette tutto al suo posto. I file esistenti con lo stesso nome vengono
    sostituiti; quelli che nel salvataggio non ci sono restano dove sono."""
    try:
        z = zipfile.ZipFile(io.BytesIO(contenuto))
    except zipfile.BadZipFile as e:
        raise ErroreSalvataggio(
            "Questo non è un file di salvataggio valido: dovrebbe essere lo .zip "
            "scaricato da «Salva tutto»."
        ) from e

    with z:
        nomi = [n for n in z.namelist() if not n.endswith("/") and n != "_salvataggio.json"]
        # Prima si controllano TUTTI i percorsi, poi si scrive: meglio non
        # ripristinare niente che ripristinare a metà.
        destinazioni = [(n, _percorso_sicuro(n)) for n in nomi]
        for nome, destinazione in destinazioni:
            destinazione.parent.mkdir(parents=True, exist_ok=True)
            destinazione.write_bytes(z.read(nome))
    return {"file_ripristinati": len(destinazioni)}


# --------------------------------------------------------------------------- #
#  Leggero: un json che sta nel browser                                        #
# --------------------------------------------------------------------------- #

def esporta_leggero() -> dict:
    """
    Dati e testo, senza gli originali caricati.

    I file di testo viaggiano come testo, così il salvataggio resta leggibile e
    correggibile a mano se mai servisse; solo l'archivio Excel, che è binario,
    viene codificato.
    """
    file: dict[str, Any] = {}
    totale = 0
    saltati = []
    for p in _file_presenti(solo_leggeri=True):
        dati = p.read_bytes()
        totale += len(dati)
        if totale > LIMITE_LEGGERO:
            saltati.append(p.relative_to(DATA_DIR).as_posix())
            continue
        nome = p.relative_to(DATA_DIR).as_posix()
        try:
            file[nome] = {"testo": dati.decode("utf-8")}
        except UnicodeDecodeError:
            file[nome] = {"base64": base64.b64encode(dati).decode("ascii")}
    return {
        "versione": 1,
        "quando": datetime.now().replace(microsecond=0).isoformat(),
        "completo": False,
        "file": file,
        "saltati_per_dimensione": saltati,
        "byte": totale,
    }


def importa_leggero(dati: dict) -> dict:
    """Rimette i file del salvataggio leggero."""
    file = (dati or {}).get("file")
    if not isinstance(file, dict):
        raise ErroreSalvataggio("Il salvataggio non contiene nessun file da ripristinare.")

    preparati = []
    for nome, voce in file.items():
        destinazione = _percorso_sicuro(nome)
        if not isinstance(voce, dict):
            raise ErroreSalvataggio(f"Voce di salvataggio illeggibile: «{nome}».")
        if "testo" in voce:
            preparati.append((destinazione, str(voce["testo"]).encode("utf-8")))
        elif "base64" in voce:
            try:
                preparati.append((destinazione, base64.b64decode(voce["base64"])))
            except Exception as e:                      # noqa: BLE001
                raise ErroreSalvataggio(f"Il file «{nome}» nel salvataggio è rovinato.") from e
        else:
            raise ErroreSalvataggio(f"Voce di salvataggio incompleta: «{nome}».")

    for destinazione, contenuto in preparati:
        destinazione.parent.mkdir(parents=True, exist_ok=True)
        destinazione.write_bytes(contenuto)
    return {"file_ripristinati": len(preparati)}
