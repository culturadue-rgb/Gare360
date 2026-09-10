"""
Assistente AI "stratega-gare".

Prompt di sistema in prompts/stratega_gare.md (placeholder). Ad ogni risposta
viene arricchito con archivio storico e tracker.

La chiave API è letta SOLO dalla variabile d'ambiente ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PROMPT_PATH = Path(os.environ.get("PROMPTS_DIR", Path(__file__).parent / "prompts")) / "stratega_gare.md"
MODELLO_DEFAULT = os.environ.get("STRATEGA_MODEL", "claude-sonnet-4-6")


def carica_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else "Sei un assistente."


def salva_prompt(testo: str) -> None:
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(testo, encoding="utf-8")


def costruisci_system(archivio_md: str, tracker: dict, includi_contesto: bool = True) -> str:
    system = carica_prompt()
    if includi_contesto:
        system += (
            "\n\n---\n# Contesto aziendale (dati reali, usali nelle risposte)\n\n"
            "## Tracker prestazioni per criterio (resa = frazione dei punti max presa di solito)\n```json\n"
            + json.dumps(tracker.get("criteri", {}), ensure_ascii=False, indent=2)
            + "\n```\n\n## Archivio storico gare (markdown)\n"
            + archivio_md
        )
    return system


def chiave_configurata() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def rispondi(messaggi: list[dict], system: str, modello: str | None = None) -> str:
    """messaggi: lista di {"role": "user"|"assistant", "content": str}."""
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return ("Nessuna chiave API configurata sul server: imposta la variabile "
                "d'ambiente ANTHROPIC_API_KEY.")
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=modello or MODELLO_DEFAULT,
        max_tokens=2000,
        system=system,
        messages=messaggi,
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


# ---------------------------------------------------------------------------
# Funzioni generiche usate dalle gare in lavorazione
# ---------------------------------------------------------------------------

def chiama(system: str, messaggi: list[dict], modello: str | None = None, max_tokens: int = 3000) -> str:
    """Chiamata generica al modello. Solleva se manca la chiave o la chiamata fallisce."""
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Nessuna chiave API configurata sul server (ANTHROPIC_API_KEY).")
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(model=modello or MODELLO_DEFAULT, max_tokens=max_tokens,
                                  system=system, messages=messaggi)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def estrai_json(istruzioni: str, testo: str, modello: str | None = None) -> dict:
    """Chiede al modello di rispondere solo con JSON e lo interpreta."""
    system = istruzioni + "\n\nRispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza testo prima o dopo e senza backtick."
    out = chiama(system, [{"role": "user", "content": testo}], modello, max_tokens=2500)
    pulito = out.strip()
    pulito = pulito[pulito.find("{"): pulito.rfind("}") + 1] if "{" in pulito else pulito
    return json.loads(pulito)


def system_gara(contesto_gara: str, archivio_md: str, tracker: dict) -> str:
    """Prompt di sistema per lavorare su una gara specifica: prompt base + metodologia + gara."""
    base = costruisci_system(archivio_md, tracker, includi_contesto=True)
    return (base + "\n\n---\n"
            "# Gara su cui stai lavorando ora\n"
            "Usa i documenti qui sotto come fonte primaria. Cita il documento da cui prendi ogni informazione. "
            "Se un'informazione non è nei documenti, dillo.\n\n" + contesto_gara)


ISTRUZIONI_VALUTAZIONE = """Valuta questa gara per decidere se partecipare. Struttura la risposta così:
1. **Sintesi** (3 righe): oggetto, ente, importo, durata, scadenza.
2. **Requisiti di partecipazione**: generali, economico-finanziari, tecnico-professionali; per ciascuno indica se dai dati aziendali (tracker/archivio) risultiamo coperti, scoperti o da verificare.
3. **Criteri di valutazione e punteggi**: tabella criterio / tipo / punti max / nostra resa attesa dal tracker / punti attesi; formula prezzo; soglia di sbarramento.
4. **Criteri premianti e leve**: dove si vincono i punti, migliorie richieste o apprezzate.
5. **Criticità e rischi**: clausole onerose, penali, tempi, personale da riassorbire, obblighi particolari.
6. **Scadenze e adempimenti**: date di sopralluogo, chiarimenti, presentazione, con ore.
7. **Confronto con gare simili in archivio**: cosa ha funzionato e dove abbiamo perso punti.
8. **Raccomandazione GO / NO GO** con motivazione e, se GO, le 3 azioni prioritarie.
Sii concreto e cita i documenti."""

ISTRUZIONI_SIMULATORE = """Dai documenti di gara estrai i dati per un simulatore di punteggio OEPV. Restituisci questo JSON:
{
 "nome": "<titolo breve>",
 "base_asta": <numero o null>,
 "punti_tecnico": <numero>,
 "punti_economico": <numero>,
 "criteri": [{"nome": "<criterio>", "tipo": "tabellare|qualitativo", "punti_max": <numero>}],
 "formula_prezzo": "lineare|proporzionale|bilineare",
 "coeff_bilineare": <0.80|0.85|0.90 o null>,
 "soglia_sbarramento": <numero o null>,
 "riparametrazione": <true|false>,
 "note_formula": "<testo della formula prezzo come scritto nel disciplinare>",
 "fonte": "<nome del documento da cui hai preso i dati>"
}
Usa "tabellare" per i criteri on/off o a punteggio automatico, "qualitativo" per quelli a giudizio della commissione.
Se la formula prezzo è a due rette (interpolazione con soglia) usa "bilineare"; se è proporzionale al ribasso usa "proporzionale"; se interpolazione lineare semplice usa "lineare"."""

ISTRUZIONI_INFO = """Dai documenti di gara estrai le informazioni chiave. Restituisci questo JSON:
{
 "titolo": "", "ente": "", "settore": "Cultura|Sociale|Altro", "cig": "", "oggetto": "",
 "importo_base_asta": <numero o null>, "durata": "", "criterio_aggiudicazione": "",
 "scadenza_offerte": "<YYYY-MM-DDTHH:MM o null>", "sopralluogo": "", "termine_chiarimenti": "",
 "requisiti": [""], "criticita": [""], "criteri_premianti": [""], "obblighi": [""], "altro": [""]
}
Se un campo non è nei documenti lascialo vuoto o null."""

ISTRUZIONI_SCADENZA = """Dal testo di un documento di gara estrai i dati per il calendario. Restituisci questo JSON:
{"titolo": "", "ente": "", "data_scadenza": "<YYYY-MM-DD o null>", "ora_scadenza": "<HH:MM o null>",
 "settore": "Cultura|Sociale|Altro", "base_asta": <numero o null>, "note": "<altre date o info rilevanti in una riga>"}
La scadenza è il termine per la presentazione delle offerte. Settore Cultura: musei, biblioteche, teatri, archivi, turismo culturale; Sociale: servizi educativi, assistenza, anziani, minori, disabilità, welfare."""
