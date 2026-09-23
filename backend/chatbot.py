"""
Assistente AI "stratega-gare".

Prompt di sistema in prompts/stratega_gare.md (placeholder). Ad ogni risposta
viene arricchito con l'archivio storico delle gare.

La chiave API è letta SOLO dalla variabile d'ambiente ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PROMPT_PATH = Path(os.environ.get("PROMPTS_DIR", Path(__file__).parent / "prompts")) / "stratega_gare.md"
MODELLO_DEFAULT = os.environ.get("STRATEGA_MODEL", "claude-opus-5")


def carica_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else "Sei un assistente."


def salva_prompt(testo: str) -> None:
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(testo, encoding="utf-8")


def costruisci_system(archivio_md: str, dati_storici: dict | None = None,
                      includi_contesto: bool = True) -> str:
    system = carica_prompt()
    if includi_contesto:
        system += (
            "\n\n---\n# Contesto aziendale (dati reali, usali nelle risposte)\n\n"
            + (("## Dati ricavati dall'archivio storico\n```json\n"
                + json.dumps(dati_storici, ensure_ascii=False, indent=2)
                + "\n```\n\n") if dati_storici else "")
            + "## Archivio storico gare\n"
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

def chiama(system: str, messaggi: list[dict], modello: str | None = None,
           max_tokens: int = 3000, ragiona: bool = False) -> str:
    """
    Chiamata generica al modello.

    `ragiona=True` accende il ragionamento esteso: serve all'analisi strategica,
    che deve mettere in fila documenti, storico e scenari. Per le estrazioni e le
    risposte sui CCNL non serve e costerebbe soltanto.

    Nota: i modelli attuali NON accettano piu' il parametro `temperature` (danno
    errore 400). La coerenza delle risposte sui CCNL non viene comunque da li',
    ma dal prompt rigido e dal controllo delle citazioni fatto dal codice.
    """
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Nessuna chiave API configurata sul server (ANTHROPIC_API_KEY).")
    client = anthropic.Anthropic(api_key=key)
    extra = {"thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}} if ragiona else {}
    resp = client.messages.create(model=modello or MODELLO_DEFAULT, max_tokens=max_tokens,
                                  system=system, messages=messaggi, **extra)
    # Con il ragionamento acceso la risposta contiene anche blocchi "thinking":
    # si tiene solo il testo.
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def estrai_json(istruzioni: str, testo: str, modello: str | None = None) -> dict:
    """Chiede al modello di rispondere solo con JSON e lo interpreta."""
    system = istruzioni + "\n\nRispondi ESCLUSIVAMENTE con un oggetto JSON valido, senza testo prima o dopo e senza backtick."
    out = chiama(system, [{"role": "user", "content": testo}], modello, max_tokens=2500)
    pulito = out.strip()
    pulito = pulito[pulito.find("{"): pulito.rfind("}") + 1] if "{" in pulito else pulito
    return json.loads(pulito)


def system_gara(contesto_gara: str, archivio_md: str, dati_storici: dict | None = None) -> str:
    """Prompt di sistema per lavorare su una gara specifica: prompt base + metodologia + gara."""
    base = costruisci_system(archivio_md, dati_storici, includi_contesto=True)
    return (base + "\n\n---\n"
            "# Gara su cui stai lavorando ora\n"
            "Usa i documenti qui sotto come fonte primaria. Cita il documento da cui prendi ogni informazione. "
            "Se un'informazione non è nei documenti, dillo.\n\n" + contesto_gara)


ISTRUZIONI_VALUTAZIONE = """Valuta questa gara per decidere se partecipare. Struttura la risposta così:
1. **Sintesi** (3 righe): oggetto, ente, importo, durata, scadenza.
2. **Requisiti di partecipazione**: generali, economico-finanziari, tecnico-professionali; per ciascuno indica se dall'archivio storico risultiamo coperti, scoperti o da verificare.
3. **Criteri di valutazione e punteggi**: tabella criterio / tipo / punti max / nostra resa attesa dall'archivio / punti attesi; formula prezzo; soglia di sbarramento.
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


# Estrazione della scheda di rilevazione completa dai documenti di gara.
# I nomi dei campi sono quelli di scheda.py: cambiare li' significa aggiornare
# anche questo elenco.
ISTRUZIONI_SCHEDA = """Dai documenti di gara (bando, disciplinare, capitolato) compila la scheda di
rilevazione dell'appalto. Restituisci SOLO questo JSON, senza commenti:

{
 "titolo": "nome breve della gara",
 "scheda": {
   "data_segnalazione": "", "settore": "Cultura|Sociale|Servizi educativi|Altro",
   "ente": "", "indirizzo_ente": "", "telefono_ente": "", "sito_ente": "",
   "servizio": "", "rup": "", "email_rup": "", "telefono_rup": "",
   "cig": "", "cup": "", "tipo_procedura": "", "criterio_aggiudicazione": "",
   "lotti": "", "piattaforma": "", "codice_procedura": "",
   "base_asta": "", "monte_ore": "", "costo_manodopera": "", "oneri_sicurezza": "",
   "ccnl": "", "durata_mesi": "", "inizio_servizio": "", "rinnovo": "", "proroga": "", "iva": "",
   "scadenza_offerte": "AAAA-MM-GG", "ora_scadenza_offerte": "HH:MM",
   "termine_quesiti": "AAAA-MM-GG", "sopralluogo": "Non previsto|Facoltativo|Obbligatorio",
   "data_sopralluogo": "AAAA-MM-GG", "seduta_pubblica": "AAAA-MM-GG",
   "requisiti": "", "documentazione_amministrativa": "", "documentazione_tecnica": "",
   "limiti_relazione": "", "gestore_uscente": "", "siamo_uscenti": "No|Si|Da verificare",
   "clausola_sociale": "", "note": ""
 },
 "criteri": {
   "peso_tecnico": "", "peso_economico": "", "soglia_sbarramento": "",
   "riparametrazione": "No|Si|Da verificare",
   "formula_economica": "Lineare / proporzionale al ribasso|Bilineare con soglia|Altra formula (la descrivo sotto)|Non applicabile",
   "coefficiente_formula": "", "formula_testo": "", "metodo_attribuzione": "",
   "elenco": [
     {"codice": "A", "criterio": "nome del criterio", "sub_criterio": "",
      "tipo": "qualitativo|tabellare", "punti_max": "", "note": ""}
   ]
 }
}

REGOLE
- Un campo che non trovi resta stringa vuota. Non dedurre, non stimare, non
  completare con quello che di solito c'e' nelle gare simili.
- Gli importi in cifre, senza simbolo di valuta.
- "formula_testo": trascrivi la formula del punteggio economico COSI' COME E'
  scritta nel disciplinare, anche se lunga. Se non corrisponde a nessuna di
  quelle previste scegli "Altra formula" e trascrivila comunque: meglio un
  calcolo non fatto che un calcolo sbagliato.
- Se due parti del disciplinare si contraddicono (capita spesso fra la tabella
  dei criteri e le formule), riporta il valore della tabella dei criteri e
  scrivi la contraddizione nel campo "note" del criterio interessato.
- Nell'elenco metti una riga per ogni criterio e, se ci sono, una riga per ogni
  sub-criterio con il criterio padre ripetuto."""


ISTRUZIONI_ANALISI = """Produci l'analisi strategica completa di questa gara, seguendo il
metodo e la struttura del tuo prompt di sistema.

Nel contesto trovi, sotto "Dati ricavati dall'archivio storico":
- scheda        la scheda di rilevazione compilata
- criteri       i criteri di punteggio e la formula economica
- risultati_simulatore  gli scenari GIA' CALCOLATI dal codice
- stime_storiche        resa tecnica, scarto dal vincitore, ribassi, concorrenti,
                        ciascuno con su quante gare si basa e con che affidabilita'
- gare_simili           i precedenti confrontabili, con id e link
- profili_concorrenti   le gare in cui si conosce il punteggio di chi ha vinto

REGOLE NON NEGOZIABILI
1. NON ricalcolare i numeri: usa quelli di risultati_simulatore e stime_storiche.
   Se un numero ti serve e non c'e', scrivi che manca e quale dato servirebbe.
2. Se uno scenario ha "calcolabile": false, NON inventare il punteggio economico:
   riporta il motivo e ragiona sul testo della formula.
3. Quando l'affidabilita' di una stima e' "bassa" o "molto bassa", dillo ogni volta
   che la usi. Una media su sei gare non e' una previsione.
4. Cita le gare precedenti per id (es. G-CUL-016), cosi' si possono ritrovare.
5. Chiudi SEMPRE con il livello di affidabilita' complessivo (Alto / Medio / Basso)
   e il motivo in una riga.

Scrivi in italiano, in markdown, senza preamboli."""
