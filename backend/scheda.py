"""
Scheda di rilevazione appalto.

I campi vengono dal modulo aziendale "Mod. SRA" (l'esempio compilato è la gara
del Comune di Salzano). Sono definiti QUI e basta: il frontend costruisce il
modulo leggendoli da /api/scheda/campi, così aggiungere un campo significa
toccare un solo file e non due.

Ogni campo può essere compilato a mano oppure proposto dall'AI leggendo bando e
disciplinare — e in entrambi i casi resta correggibile, prima e dopo il
salvataggio.

I criteri di punteggio stanno a parte (CAMPI_CRITERI + la lista dei criteri):
sono quelli che alimentano il simulatore.
"""

from __future__ import annotations

from typing import Any

# Tipi ammessi: testo, testo_lungo, numero, data, ora, scelta, si_no
SEZIONI: list[dict[str, Any]] = [
    {
        "id": "anagrafica",
        "titolo": "Ente e servizio",
        "campi": [
            {"id": "data_segnalazione", "etichetta": "Data segnalazione procedura", "tipo": "data"},
            {"id": "settore", "etichetta": "Settore", "tipo": "scelta",
             "opzioni": ["Cultura", "Sociale", "Servizi educativi", "Altro"]},
            {"id": "ente", "etichetta": "Ente / stazione appaltante", "tipo": "testo", "obbligatorio": True},
            {"id": "indirizzo_ente", "etichetta": "Indirizzo", "tipo": "testo"},
            {"id": "telefono_ente", "etichetta": "Telefono", "tipo": "testo"},
            {"id": "sito_ente", "etichetta": "Sito web", "tipo": "testo"},
            {"id": "servizio", "etichetta": "Servizio / oggetto dell'appalto", "tipo": "testo_lungo",
             "obbligatorio": True},
            {"id": "rup", "etichetta": "Responsabile del procedimento", "tipo": "testo"},
            {"id": "email_rup", "etichetta": "Email del responsabile", "tipo": "testo"},
            {"id": "telefono_rup", "etichetta": "Telefono del responsabile", "tipo": "testo"},
        ],
    },
    {
        "id": "procedura",
        "titolo": "Procedura",
        "campi": [
            {"id": "cig", "etichetta": "CIG", "tipo": "testo"},
            {"id": "cup", "etichetta": "CUP", "tipo": "testo"},
            {"id": "tipo_procedura", "etichetta": "Tipo di procedura", "tipo": "scelta",
             "opzioni": ["Aperta", "Negoziata", "Ristretta", "Affidamento diretto",
                         "Concessione", "Coprogettazione", "Altro"]},
            {"id": "criterio_aggiudicazione", "etichetta": "Criterio di aggiudicazione", "tipo": "scelta",
             "opzioni": ["OEPV (qualità/prezzo)", "Solo offerta tecnica", "Massimo ribasso"]},
            {"id": "lotti", "etichetta": "Lotti", "tipo": "testo", "aiuto": "es. lotto unico, oppure 3 lotti"},
            {"id": "piattaforma", "etichetta": "Piattaforma telematica (link)", "tipo": "testo"},
            {"id": "codice_procedura", "etichetta": "Codice / n. gara sulla piattaforma", "tipo": "testo"},
        ],
    },
    {
        "id": "economia",
        "titolo": "Importi e durata",
        "campi": [
            {"id": "base_asta", "etichetta": "Importo a base di gara (€)", "tipo": "numero"},
            {"id": "monte_ore", "etichetta": "Monte ore a base di gara", "tipo": "numero"},
            {"id": "costo_manodopera", "etichetta": "Costo della manodopera indicato (€)", "tipo": "numero"},
            {"id": "oneri_sicurezza", "etichetta": "Oneri sicurezza non ribassabili (€)", "tipo": "numero"},
            {"id": "ccnl", "etichetta": "CCNL indicato dalla stazione appaltante", "tipo": "testo"},
            {"id": "durata_mesi", "etichetta": "Durata (mesi)", "tipo": "numero"},
            {"id": "inizio_servizio", "etichetta": "Inizio previsto del servizio", "tipo": "data"},
            {"id": "rinnovo", "etichetta": "Rinnovo previsto", "tipo": "testo"},
            {"id": "proroga", "etichetta": "Proroga prevista", "tipo": "testo"},
            {"id": "iva", "etichetta": "Regime IVA", "tipo": "testo"},
        ],
    },
    {
        "id": "scadenze",
        "titolo": "Date",
        "aiuto": "Passando la gara in lavorazione queste date entrano nel calendario.",
        "campi": [
            {"id": "scadenza_offerte", "etichetta": "Termine presentazione offerte", "tipo": "data",
             "calendario": "termine offerte"},
            {"id": "ora_scadenza_offerte", "etichetta": "Ora", "tipo": "ora"},
            {"id": "termine_quesiti", "etichetta": "Termine per i quesiti", "tipo": "data",
             "calendario": "quesiti"},
            {"id": "sopralluogo", "etichetta": "Sopralluogo", "tipo": "scelta",
             "opzioni": ["Non previsto", "Facoltativo", "Obbligatorio"]},
            {"id": "data_sopralluogo", "etichetta": "Data del sopralluogo", "tipo": "data",
             "calendario": "sopralluogo"},
            {"id": "seduta_pubblica", "etichetta": "Prima seduta pubblica", "tipo": "data",
             "calendario": "seduta pubblica"},
        ],
    },
    {
        "id": "requisiti",
        "titolo": "Requisiti e documentazione",
        "campi": [
            {"id": "requisiti", "etichetta": "Requisiti richiesti", "tipo": "testo_lungo"},
            {"id": "documentazione_amministrativa", "etichetta": "Documentazione amministrativa", "tipo": "testo_lungo"},
            {"id": "documentazione_tecnica", "etichetta": "Documentazione tecnica", "tipo": "testo_lungo"},
            {"id": "limiti_relazione", "etichetta": "Limiti della relazione tecnica", "tipo": "testo",
             "aiuto": "es. massimo 20 facciate"},
        ],
    },
    {
        "id": "contesto",
        "titolo": "Contesto e valutazioni",
        "campi": [
            {"id": "gestore_uscente", "etichetta": "Attuale gestore del servizio", "tipo": "testo"},
            {"id": "siamo_uscenti", "etichetta": "Siamo noi il gestore uscente?", "tipo": "scelta",
             "opzioni": ["No", "Sì", "Da verificare"]},
            {"id": "clausola_sociale", "etichetta": "Clausola sociale", "tipo": "testo"},
            {"id": "note", "etichetta": "Note", "tipo": "testo_lungo"},
        ],
    },
]

# Le modalità di attribuzione del punteggio: alimentano il simulatore.
CAMPI_CRITERI: list[dict[str, Any]] = [
    {"id": "peso_tecnico", "etichetta": "Punti offerta tecnica", "tipo": "numero"},
    {"id": "peso_economico", "etichetta": "Punti offerta economica", "tipo": "numero",
     "aiuto": "0 se la gara è a sola offerta tecnica"},
    {"id": "soglia_sbarramento", "etichetta": "Soglia di sbarramento tecnico", "tipo": "numero",
     "aiuto": "punti tecnici minimi per non essere esclusi; vuoto se non prevista"},
    {"id": "riparametrazione", "etichetta": "Riparametrazione", "tipo": "scelta",
     "opzioni": ["No", "Sì", "Da verificare"]},
    {"id": "formula_economica", "etichetta": "Formula del punteggio economico", "tipo": "scelta",
     "opzioni": ["Lineare / proporzionale al ribasso", "Bilineare con soglia",
                 "Altra formula (la descrivo sotto)", "Non applicabile"]},
    {"id": "coefficiente_formula", "etichetta": "Coefficiente della formula (X)", "tipo": "numero",
     "aiuto": "solo per la bilineare: di solito 0,80 / 0,85 / 0,90"},
    {"id": "formula_testo", "etichetta": "Formula come scritta nel disciplinare", "tipo": "testo_lungo",
     "aiuto": "trascrivila sempre: se non rientra fra quelle previste il simulatore non la approssima"},
    {"id": "metodo_attribuzione", "etichetta": "Metodo di attribuzione dei coefficienti", "tipo": "testo",
     "aiuto": "es. confronto a coppie, media dei coefficienti discrezionali"},
]

# Un singolo criterio di punteggio.
COLONNE_CRITERIO = ["codice", "criterio", "sub_criterio", "tipo", "punti_max", "note"]
TIPI_CRITERIO = ["qualitativo", "tabellare"]


def campi_piatti() -> list[dict]:
    """Tutti i campi della scheda, senza le sezioni. Serve a validare."""
    return [c for s in SEZIONI for c in s["campi"]]


def scheda_vuota() -> dict:
    return {c["id"]: "" for c in campi_piatti()}


def criteri_vuoti() -> dict:
    return {c["id"]: "" for c in CAMPI_CRITERI}


def normalizza_scheda(dati: dict | None) -> dict:
    """Tiene solo i campi conosciuti e li porta a testo. Ignora il resto."""
    dati = dati or {}
    ammessi = {c["id"] for c in campi_piatti()}
    return {k: ("" if v is None else str(v).strip()) for k, v in dati.items() if k in ammessi}


def normalizza_criteri(dati: dict | None) -> dict:
    """Le modalità di punteggio più l'elenco dei criteri."""
    dati = dati or {}
    # Si parte da tutte le chiavi previste, così il modulo nel frontend trova
    # sempre qualcosa a cui agganciarsi, anche su una gara appena creata.
    fuori = criteri_vuoti()
    fuori.update({k: ("" if v is None else str(v).strip())
                  for k, v in dati.items() if k in fuori})

    elenco = []
    for riga in (dati.get("elenco") or []):
        if not isinstance(riga, dict):
            continue
        voce = {c: ("" if riga.get(c) is None else str(riga.get(c, "")).strip())
                for c in COLONNE_CRITERIO}
        if voce["criterio"] or voce["codice"]:
            if voce["tipo"] not in TIPI_CRITERIO:
                voce["tipo"] = "qualitativo"
            elenco.append(voce)
    fuori["elenco"] = elenco
    return fuori


def somma_criteri(criteri: dict | None) -> float:
    """Somma dei punti massimi dichiarati nei criteri."""
    totale = 0.0
    for riga in ((criteri or {}).get("elenco") or []):
        try:
            totale += float(str(riga.get("punti_max", "")).replace(",", "."))
        except (TypeError, ValueError):
            continue
    return round(totale, 2)


def controlla(criteri: dict | None) -> list[str]:
    """
    Avvisi sulle incoerenze, senza bloccare nulla: un disciplinare può davvero
    contenere numeri che non tornano (succede), e in quel caso va registrato
    com'è, non "aggiustato".
    """
    criteri = criteri or {}
    avvisi = []

    def num(k):
        try:
            return float(str(criteri.get(k, "")).replace(",", "."))
        except (TypeError, ValueError):
            return None

    tecnico, economico = num("peso_tecnico"), num("peso_economico")
    if tecnico is not None and economico is not None and tecnico + economico not in (0, 100):
        avvisi.append(
            f"Tecnico ({tecnico:g}) + economico ({economico:g}) fa {tecnico + economico:g} invece di 100. "
            "Se è così anche nel disciplinare va bene, ma vale la pena ricontrollare."
        )

    somma = somma_criteri(criteri)
    if tecnico is not None and somma and abs(somma - tecnico) > 0.01:
        avvisi.append(
            f"I criteri elencati sommano {somma:g} punti, ma l'offerta tecnica ne vale {tecnico:g}. "
            "Spesso significa che manca un criterio, o che due tabelle del disciplinare non concordano."
        )

    soglia = num("soglia_sbarramento")
    if soglia is not None and tecnico is not None and soglia > tecnico:
        avvisi.append(
            f"La soglia di sbarramento ({soglia:g}) supera i punti tecnici disponibili ({tecnico:g})."
        )

    if criteri.get("formula_economica") == "Altra formula (la descrivo sotto)" \
            and not criteri.get("formula_testo"):
        avvisi.append(
            "Hai indicato una formula diversa da quelle previste ma non l'hai trascritta: "
            "senza il testo il simulatore non può calcolare il punteggio economico."
        )

    return avvisi
