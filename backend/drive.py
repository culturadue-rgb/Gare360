"""
Collegamento a Google Drive e Google Fogli.

PERCHE' ESISTE
--------------
Su Render, piano gratuito, il disco del server si svuota a ogni riavvio: tutto
quello che l'app scrive lì prima o poi sparisce. Quindi i dati veri (gare,
documenti, archivio, calendario) vivono su Google Drive, in UNA SOLA COPIA.
L'app legge e scrive lì; il disco locale serve solo da deposito temporaneo.

Conseguenza voluta: le correzioni fatte a mano nei fogli si vedono nell'app, e
le modifiche dell'app si vedono nei fogli. Non ci sono due verità.

COME SI COLLEGA
---------------
Account Gmail personale, non Workspace: niente service account. Si usa un
"refresh token" ottenuto una volta sola dal browser, che poi vale finché non
viene revocato (purché la schermata di consenso Google sia "In produzione" e
non "In test", altrimenti scade dopo 7 giorni).

Tre variabili d'ambiente, da impostare su Render e MAI nel repository:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REFRESH_TOKEN

Facoltative:
    GARE360_CARTELLA        nome della cartella principale (default "Gare360")
    GARE360_ARCHIVIO_ID     id del foglio Archivio_Gare360, se già esiste
    GARE360_DATI_ID         id del foglio Gare360_Dati, se già esiste

SE IL COLLEGAMENTO SALTA
------------------------
Tutte le funzioni sollevano AccessoGoogleScaduto con un messaggio in italiano
che dice cosa fare. L'app lo mostra all'utente invece di un errore tecnico.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Iterable, Optional

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"

MIME_CARTELLA = "application/vnd.google-apps.folder"
MIME_FOGLIO = "application/vnd.google-apps.spreadsheet"

TIMEOUT = 30
SECONDI_CACHE = 90  # le letture ripetute entro un minuto e mezzo non ripartono


# --------------------------------------------------------------------------- #
#  Errori                                                                      #
# --------------------------------------------------------------------------- #

class ErroreDrive(Exception):
    """Errore generico parlando con Google."""


class AccessoGoogleScaduto(ErroreDrive):
    """Le credenziali non funzionano più: va rifatto il collegamento."""

    def __init__(self, dettaglio: str = ""):
        super().__init__(
            "Accesso a Google scaduto o non valido: rinnovalo. "
            "Le istruzioni sono nel README, sezione «Rinnovare l'accesso a Google». "
            + (f"({dettaglio})" if dettaglio else "")
        )


class ConfigurazioneMancante(ErroreDrive):
    """Le tre variabili d'ambiente non sono state impostate."""

    def __init__(self, mancanti: list[str]):
        super().__init__(
            "Google Drive non è ancora collegato: mancano le variabili d'ambiente "
            + ", ".join(mancanti)
            + ". Vanno impostate su Render (Environment → Add Environment Variable)."
        )


class IntestazioniCambiate(ErroreDrive):
    """Qualcuno ha cambiato le colonne del foglio: non si scrive alla cieca."""


# --------------------------------------------------------------------------- #
#  Credenziali e token                                                         #
# --------------------------------------------------------------------------- #

_lucchetto = threading.Lock()
_token_cache: dict[str, Any] = {"valore": None, "scade": 0.0}


def configurato() -> bool:
    """Vero se le tre variabili ci sono. Serve a mostrare messaggi utili."""
    return all(os.environ.get(k, "").strip() for k in
               ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"))


def _credenziali() -> tuple[str, str, str]:
    valori = {k: os.environ.get(k, "").strip() for k in
              ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")}
    mancanti = [k for k, v in valori.items() if not v]
    if mancanti:
        raise ConfigurazioneMancante(mancanti)
    return valori["GOOGLE_CLIENT_ID"], valori["GOOGLE_CLIENT_SECRET"], valori["GOOGLE_REFRESH_TOKEN"]


def _token() -> str:
    """
    Token d'accesso valido. Dura un'ora: lo si riusa finché regge, e si rinnova
    un minuto prima della scadenza per non farsi trovare scoperti a metà di
    un'operazione.
    """
    with _lucchetto:
        if _token_cache["valore"] and time.time() < _token_cache["scade"]:
            return _token_cache["valore"]

        client_id, client_secret, refresh_token = _credenziali()
        try:
            r = requests.post(TOKEN_URL, timeout=TIMEOUT, data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
        except requests.RequestException as e:
            raise ErroreDrive(f"Google non raggiungibile: {e}") from e

        if r.status_code in (400, 401):
            # invalid_grant = token revocato, scaduto (consenso in "Test"), o
            # password dell'account cambiata.
            raise AccessoGoogleScaduto(r.json().get("error", r.text[:200]) if r.content else "")
        if not r.ok:
            raise ErroreDrive(f"Errore nel rinnovo del token ({r.status_code}): {r.text[:200]}")

        dati = r.json()
        _token_cache["valore"] = dati["access_token"]
        _token_cache["scade"] = time.time() + int(dati.get("expires_in", 3600)) - 60
        return _token_cache["valore"]


def _intestazioni() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def _chiama(metodo: str, url: str, **kw) -> Any:
    """Una richiesta a Google, con gli errori tradotti in italiano."""
    kw.setdefault("timeout", TIMEOUT)
    intest = kw.pop("headers", {})
    try:
        r = requests.request(metodo, url, headers={**_intestazioni(), **intest}, **kw)
    except requests.RequestException as e:
        raise ErroreDrive(f"Google non raggiungibile: {e}") from e

    if r.status_code in (401, 403):
        # 403 può anche essere "quota superata": si distingue dal messaggio.
        testo = r.text[:300]
        if "rateLimit" in testo or "quota" in testo.lower():
            raise ErroreDrive("Google ha temporaneamente rifiutato le richieste "
                              "(troppe in poco tempo). Riprova fra un minuto.")
        raise AccessoGoogleScaduto(testo)
    if r.status_code == 404:
        raise ErroreDrive(f"Non trovato su Drive: {url}")
    if not r.ok:
        raise ErroreDrive(f"Errore Google {r.status_code}: {r.text[:300]}")

    if not r.content:
        return None
    try:
        return r.json()
    except ValueError:
        return r.content


# --------------------------------------------------------------------------- #
#  Cache brevissima delle letture                                              #
# --------------------------------------------------------------------------- #

_cache: dict[str, tuple[float, Any]] = {}


def svuota_cache(prefisso: str = "") -> None:
    """Dopo una scrittura la lettura corrispondente non è più valida."""
    with _lucchetto:
        for k in [k for k in _cache if k.startswith(prefisso)]:
            _cache.pop(k, None)


def _con_cache(chiave: str, produci):
    ora = time.time()
    voce = _cache.get(chiave)
    if voce and ora - voce[0] < SECONDI_CACHE:
        return voce[1]
    valore = produci()
    _cache[chiave] = (ora, valore)
    return valore


# --------------------------------------------------------------------------- #
#  Drive: cartelle e file                                                      #
# --------------------------------------------------------------------------- #

def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def cerca(query: str, campi: str = "files(id,name,mimeType,modifiedTime,size)") -> list[dict]:
    """Elenca i file che corrispondono alla query Drive (non cestinati)."""
    voci, pagina = [], None
    while True:
        params = {"q": f"({query}) and trashed = false", "fields": f"nextPageToken,{campi}",
                  "pageSize": 200, "spaces": "drive"}
        if pagina:
            params["pageToken"] = pagina
        dati = _chiama("GET", f"{DRIVE_API}/files", params=params)
        voci.extend(dati.get("files", []))
        pagina = dati.get("nextPageToken")
        if not pagina:
            return voci


def trova_cartella(nome: str, genitore: Optional[str] = None) -> Optional[str]:
    q = f"mimeType = '{MIME_CARTELLA}' and name = '{_escape(nome)}'"
    if genitore:
        q += f" and '{genitore}' in parents"
    trovate = cerca(q, campi="files(id,name)")
    return trovate[0]["id"] if trovate else None


def crea_cartella(nome: str, genitore: Optional[str] = None) -> str:
    corpo: dict[str, Any] = {"name": nome, "mimeType": MIME_CARTELLA}
    if genitore:
        corpo["parents"] = [genitore]
    return _chiama("POST", f"{DRIVE_API}/files", json=corpo, params={"fields": "id"})["id"]


def cartella(nome: str, genitore: Optional[str] = None) -> str:
    """Id della cartella, creandola se non c'è. Idempotente."""
    esistente = trova_cartella(nome, genitore)
    return esistente or crea_cartella(nome, genitore)


def cartella_principale() -> str:
    """La cartella "Gare360" in cima, sotto cui sta tutto il resto."""
    nome = os.environ.get("GARE360_CARTELLA", "Gare360").strip() or "Gare360"
    return _con_cache(f"cartella:{nome}", lambda: cartella(nome))


def carica_file(nome: str, contenuto: bytes, cartella_id: str,
                mime: str = "application/octet-stream") -> dict:
    """Carica un file nella cartella indicata. Restituisce {id, name}."""
    metadati = json.dumps({"name": nome, "parents": [cartella_id]}).encode("utf-8")
    parti = {
        "metadata": ("metadata", metadati, "application/json; charset=UTF-8"),
        "file": (nome, contenuto, mime),
    }
    return _chiama("POST", f"{DRIVE_UPLOAD}/files",
                   params={"uploadType": "multipart", "fields": "id,name,size,mimeType"},
                   files=parti)


def scarica_file(file_id: str) -> bytes:
    return _chiama("GET", f"{DRIVE_API}/files/{file_id}", params={"alt": "media"})


def elimina_file(file_id: str) -> None:
    """Sposta nel cestino: recuperabile per 30 giorni, non distrutto."""
    _chiama("PATCH", f"{DRIVE_API}/files/{file_id}", json={"trashed": True})


def url_file(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"


def url_cartella(cartella_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{cartella_id}"


# --------------------------------------------------------------------------- #
#  Fogli Google                                                                #
# --------------------------------------------------------------------------- #

def trova_foglio(nome: str, genitore: Optional[str] = None) -> Optional[str]:
    q = f"mimeType = '{MIME_FOGLIO}' and name = '{_escape(nome)}'"
    if genitore:
        q += f" and '{genitore}' in parents"
    trovati = cerca(q, campi="files(id,name)")
    return trovati[0]["id"] if trovati else None


def crea_foglio(nome: str, genitore: Optional[str] = None, schede: Iterable[str] = ()) -> str:
    corpo: dict[str, Any] = {"properties": {"title": nome}}
    schede = list(schede)
    if schede:
        corpo["sheets"] = [{"properties": {"title": t}} for t in schede]
    foglio_id = _chiama("POST", SHEETS_API, json=corpo, params={"fields": "spreadsheetId"})["spreadsheetId"]
    if genitore:
        # Un foglio creato via Sheets nasce nella radice: lo si sposta.
        _chiama("PATCH", f"{DRIVE_API}/files/{foglio_id}",
                params={"addParents": genitore, "removeParents": "root", "fields": "id"})
    return foglio_id


def schede(foglio_id: str) -> list[str]:
    dati = _chiama("GET", f"{SHEETS_API}/{foglio_id}", params={"fields": "sheets.properties.title"})
    return [s["properties"]["title"] for s in dati.get("sheets", [])]


def aggiungi_scheda(foglio_id: str, titolo: str) -> None:
    if titolo in schede(foglio_id):
        return
    _chiama("POST", f"{SHEETS_API}/{foglio_id}:batchUpdate",
            json={"requests": [{"addSheet": {"properties": {"title": titolo}}}]})


def leggi(foglio_id: str, scheda: str) -> list[list[str]]:
    """Tutte le righe di una scheda, come liste di stringhe."""
    def scarica():
        dati = _chiama("GET", f"{SHEETS_API}/{foglio_id}/values/{requests.utils.quote(scheda)}",
                       params={"majorDimension": "ROWS", "valueRenderOption": "UNFORMATTED_VALUE"})
        return [[("" if c is None else str(c)) for c in riga] for riga in dati.get("values", [])]
    return _con_cache(f"foglio:{foglio_id}:{scheda}", scarica)


def leggi_dizionari(foglio_id: str, scheda: str, riga_intestazioni: int = 1) -> tuple[list[str], list[dict]]:
    """
    (intestazioni, righe) dove ogni riga è un dizionario colonna -> valore.
    `riga_intestazioni` è 1 per i fogli normali; alcuni fogli hanno il titolo
    in cima e le intestazioni più sotto.
    """
    righe = leggi(foglio_id, scheda)
    if len(righe) < riga_intestazioni:
        return [], []
    intestazioni = [c.strip() for c in righe[riga_intestazioni - 1]]
    fuori = []
    for riga in righe[riga_intestazioni:]:
        valori = list(riga) + [""] * (len(intestazioni) - len(riga))
        fuori.append({h: valori[i] for i, h in enumerate(intestazioni) if h})
    return intestazioni, fuori


def verifica_intestazioni(foglio_id: str, scheda: str, attese: list[str],
                          riga_intestazioni: int = 1) -> None:
    """
    Prima di ogni scrittura: le colonne sono ancora quelle che ci aspettiamo?
    Se qualcuno le ha rinominate o spostate, si BLOCCA e dice quale non torna,
    invece di scrivere i valori nelle colonne sbagliate.
    """
    righe = leggi(foglio_id, scheda)
    presenti = [c.strip() for c in righe[riga_intestazioni - 1]] if len(righe) >= riga_intestazioni else []
    if not presenti:
        raise IntestazioniCambiate(
            f"Il foglio «{scheda}» non ha intestazioni alla riga {riga_intestazioni}: "
            "la scrittura è bloccata per non rovinare i dati."
        )
    for i, atteso in enumerate(attese):
        trovato = presenti[i] if i < len(presenti) else "(niente)"
        if trovato.strip().lower() != atteso.strip().lower():
            raise IntestazioniCambiate(
                f"Nel foglio «{scheda}» la colonna {i + 1} dovrebbe chiamarsi "
                f"«{atteso}» e invece si chiama «{trovato}». "
                "La scrittura è bloccata: rimetti a posto l'intestazione, oppure "
                "dimmi che la nuova struttura è quella giusta."
            )


def aggiungi_righe(foglio_id: str, scheda: str, righe: list[list[Any]]) -> None:
    """Accoda righe in fondo. Una sola chiamata per tutte: meno richieste a Google."""
    if not righe:
        return
    _chiama("POST", f"{SHEETS_API}/{foglio_id}/values/{requests.utils.quote(scheda)}:append",
            params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
            json={"values": [[("" if v is None else v) for v in r] for r in righe]})
    svuota_cache(f"foglio:{foglio_id}:{scheda}")


def scrivi_intervallo(foglio_id: str, intervallo: str, righe: list[list[Any]]) -> None:
    """Sovrascrive un intervallo preciso, es. 'Gare!A5:AH5'."""
    _chiama("PUT", f"{SHEETS_API}/{foglio_id}/values/{requests.utils.quote(intervallo)}",
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": [[("" if v is None else v) for v in r] for r in righe]})
    svuota_cache(f"foglio:{foglio_id}:")


def _id_scheda(foglio_id: str, scheda: str) -> int:
    dati = _chiama("GET", f"{SHEETS_API}/{foglio_id}",
                   params={"fields": "sheets.properties(sheetId,title)"})
    for s in dati.get("sheets", []):
        if s["properties"]["title"] == scheda:
            return s["properties"]["sheetId"]
    raise ErroreDrive(f"Scheda «{scheda}» non trovata nel foglio.")


def elimina_riga(foglio_id: str, scheda: str, numero_riga: int) -> None:
    """Cancella una riga (numerata come la vedi nel foglio, partendo da 1)."""
    sid = _id_scheda(foglio_id, scheda)
    _chiama("POST", f"{SHEETS_API}/{foglio_id}:batchUpdate", json={"requests": [{
        "deleteDimension": {"range": {"sheetId": sid, "dimension": "ROWS",
                                      "startIndex": numero_riga - 1, "endIndex": numero_riga}}
    }]})
    svuota_cache(f"foglio:{foglio_id}:{scheda}")


def colonna_lettera(indice: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA. Serve a comporre gli intervalli."""
    lettere = ""
    while indice > 0:
        indice, resto = divmod(indice - 1, 26)
        lettere = chr(65 + resto) + lettere
    return lettere


# --------------------------------------------------------------------------- #
#  Diagnostica                                                                 #
# --------------------------------------------------------------------------- #

def stato() -> dict:
    """Riassunto per l'app: il collegamento funziona? Serve a /api/health."""
    if not configurato():
        return {"collegato": False, "motivo": "credenziali non impostate"}
    try:
        _token()
        principale = cartella_principale()
        return {"collegato": True, "cartella_principale": principale,
                "url": url_cartella(principale)}
    except ErroreDrive as e:
        return {"collegato": False, "motivo": str(e)}
