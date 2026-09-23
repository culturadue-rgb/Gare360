"""
Il ponte manuale: usare l'app senza chiave API.

PERCHE' ESISTE
--------------
Le chiavi API di Anthropic si pagano a consumo. Chi non puo' averne una
resterebbe senza le tre funzioni che usano l'AI: compilare la scheda da un PDF,
l'analisi strategica, la consultazione dei CCNL. Ma un abbonamento a Claude sul
sito c'e' gia', e la differenza fra le due strade e' solo CHI preme il pulsante.

Quindi qui l'app prepara il testo da incollare su claude.ai, e riprende la
risposta incollata indietro. Il risultato finisce dove sarebbe finito comunque:
la stessa scheda, lo stesso archivio delle analisi, lo stesso controllo delle
citazioni. Piu' lento, non piu' povero.

COSA NON CAMBIA
---------------
I numeri continuano a farli il simulatore, non l'AI: la parte deterministica
dell'app non ha mai avuto bisogno di una chiave. E la verifica delle citazioni
sui CCNL gira sul testo incollato esattamente come girava sulla risposta
dell'API, perche' e' codice, non fiducia.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import scheda as mod_scheda

# Quanto testo si puo' ragionevolmente incollare in una conversazione. Oltre
# questa soglia si avvisa: meglio saperlo prima di copiare, non dopo.
LIMITE_COMODO = 100_000


def avviso_lunghezza(testo: str) -> str:
    """Un avviso solo quando serve davvero."""
    n = len(testo)
    if n <= LIMITE_COMODO:
        return ""
    return (f"Il testo è lungo {n:,} caratteri".replace(",", ".") +
            ": potrebbe non entrare tutto in un solo messaggio. Se Claude si lamenta, "
            "incolla prima la parte iniziale e poi il resto in un secondo messaggio.")


# --------------------------------------------------------------------------- #
#  Scheda di rilevazione: dal PDF ai campi, passando dalle mani dell'utente    #
# --------------------------------------------------------------------------- #

def istruzioni_scheda() -> str:
    """
    Si chiede un elenco «campo: valore», non JSON.

    Il JSON e' comodo per un programma e ostile per una persona: basta una
    virgola fuori posto e non si capisce cosa sia andato storto. Un elenco di
    righe si legge, si corregge a mano e si incolla senza paura.
    """
    righe = [f"- {c['etichetta']}" + (f" (valori ammessi: {', '.join(c['opzioni'])})"
                                      if c.get("opzioni") else "")
             for c in mod_scheda.campi_piatti()]
    return (
        "Leggi i documenti di gara qui sotto e compila questa scheda.\n\n"
        "RISPONDI SOLO con un elenco di righe nella forma «Nome del campo: valore», "
        "una per riga, senza commenti prima o dopo.\n"
        "Lascia FUORI le righe che non sai compilare: un campo vuoto si riconosce, "
        "un campo inventato no.\n"
        "Le date scrivile come GG/MM/AAAA. Gli importi in euro con la virgola decimale.\n\n"
        "Campi da compilare:\n" + "\n".join(righe) + "\n\n"
        "Dopo la scheda, se nei documenti ci sono i criteri di valutazione, aggiungi "
        "una riga «CRITERI:» e sotto una riga per criterio nella forma:\n"
        "codice | criterio | sub-criterio | tipo (discrezionale/tabellare/automatico) | punti massimi\n"
    )


def testo_per_scheda(testo_documento: str, nome_file: str = "") -> str:
    """Il messaggio completo da incollare: istruzioni più documento."""
    intestazione = f"(documento: {nome_file})\n\n" if nome_file else ""
    return (istruzioni_scheda() + "\n" + "=" * 60 + "\nDOCUMENTI DI GARA\n" + "=" * 60 +
            "\n\n" + intestazione + testo_documento)


def _varianti(etichetta: str) -> list[str]:
    """
    I modi plausibili di scrivere la stessa etichetta.

    "Ente / stazione appaltante" va riconosciuto anche se torna indietro come
    "Stazione appaltante", e "Importo a base di gara (€)" anche senza il simbolo
    fra parentesi: chi ricopia una scheda scrive il nome che gli viene, e
    rifiutarlo per una barra vorrebbe dire perdere un dato che c'era.
    """
    fuori = [etichetta]
    senza_parentesi = re.sub(r"\([^)]*\)", " ", etichetta)
    fuori.append(senza_parentesi)
    fuori.extend(senza_parentesi.split("/"))
    return [v for v in (_norm(x) for x in fuori) if v]


def _indice_etichette() -> dict[str, str]:
    """
    Da etichetta (e da id) al nome del campo.

    Se due campi diversi rivendicano la stessa scrittura, vince il primo: si
    preferisce un accostamento stabile a uno che cambia con l'ordine dei campi.
    """
    indice: dict[str, str] = {}
    for c in mod_scheda.campi_piatti():
        for v in _varianti(c["etichetta"]) + [_norm(c["id"])]:
            indice.setdefault(v, c["id"])
    return indice


def _norm(s: str) -> str:
    """Confronto indulgente: senza accenti, maiuscole e punteggiatura."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def leggi_scheda_incollata(testo: str) -> dict:
    """
    Trasforma l'elenco «campo: valore» in una scheda.

    Non si butta via niente in silenzio: le righe non riconosciute tornano
    indietro nell'elenco `non_riconosciute`, cosi' si vede cosa e' rimasto fuori
    e si decide a mano, invece di scoprire un campo vuoto tre giorni dopo.
    """
    indice = _indice_etichette()
    campi: dict[str, str] = {}
    non_riconosciute: list[str] = []
    righe_criteri: list[str] = []
    titolo = ""
    dentro_criteri = False

    for riga in (testo or "").splitlines():
        grezza = riga.strip().lstrip("-•*").strip()
        if not grezza:
            continue
        if _norm(grezza).startswith("criteri"):
            dentro_criteri = True
            continue
        if dentro_criteri:
            if "|" in grezza:
                righe_criteri.append(grezza)
            else:
                non_riconosciute.append(grezza)
            continue
        if ":" not in grezza:
            non_riconosciute.append(grezza)
            continue
        etichetta, valore = grezza.split(":", 1)
        valore = valore.strip().strip("*").strip()
        chiave = indice.get(_norm(etichetta))
        if chiave and valore and _norm(valore) not in ("", "n d", "nd", "non indicato",
                                                       "non presente", "da verificare"):
            campi[chiave] = valore
        elif _norm(etichetta) in ("titolo", "titolo gara", "oggetto", "oggetto della gara"):
            titolo = valore
        elif valore:
            non_riconosciute.append(grezza)

    criteri = _leggi_criteri(righe_criteri)
    return {
        "titolo": titolo or campi.get("oggetto", "") or campi.get("stazione_appaltante", ""),
        "scheda": mod_scheda.normalizza_scheda(campi),
        "criteri": criteri,
        "avvisi": mod_scheda.controlla(criteri),
        "non_riconosciute": non_riconosciute,
        "campi_compilati": len(campi),
    }


def _leggi_criteri(righe: list[str]) -> dict:
    """Le righe «codice | criterio | sub | tipo | punti» diventano l'elenco."""
    elenco = []
    for r in righe:
        pezzi = [p.strip() for p in r.split("|")]
        if not any(pezzi):
            continue
        # Una riga di intestazione ("codice | criterio | ...") non e' un criterio.
        if _norm(pezzi[0]) in ("codice", "cod", "n", "num"):
            continue
        while len(pezzi) < 5:
            pezzi.append("")
        elenco.append({"codice": pezzi[0], "criterio": pezzi[1], "sub_criterio": pezzi[2],
                       "tipo": pezzi[3], "punti_max": pezzi[4],
                       "note": " | ".join(pezzi[5:]).strip()})
    return mod_scheda.normalizza_criteri({"elenco": elenco} if elenco else None)


# --------------------------------------------------------------------------- #
#  Analisi strategica e CCNL: qui il testo e' gia' pronto altrove              #
# --------------------------------------------------------------------------- #

def testo_per_analisi(system: str, istruzioni: str) -> str:
    """
    Il prompt di sistema e la richiesta, uniti in un unico messaggio.

    Nell'uso via API sono due cose diverse; incollandoli a mano diventano un
    testo solo, e va bene: cambia il modo di consegnarli, non il contenuto.
    """
    return (system + "\n\n" + "=" * 60 + "\nCOSA DEVI PRODURRE\n" + "=" * 60 + "\n\n" +
            istruzioni)


def testo_per_ccnl(system: str, domanda: str) -> str:
    """I passaggi trovati dal codice piu' la domanda. I passaggi restano quelli:
    e' il motivo per cui la verifica delle citazioni funziona anche cosi'."""
    return (system + "\n\n" + "=" * 60 + "\nDOMANDA\n" + "=" * 60 + "\n\n" + domanda)
