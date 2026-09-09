"""
Archivio storico gare (data/storico-gare.md).

Il file resta in markdown leggibile (stesso formato del template del progetto),
così può essere modificato anche a mano. Questo modulo:
  - legge le schede e ne estrae i dati strutturati (esito, ribassi, tabella criteri)
  - aggiunge una nuova scheda in coda
"""

from __future__ import annotations

import re
from pathlib import Path

ARCHIVIO_PATH = Path(__file__).parent / "data" / "storico-gare.md"

_RE_SCHEDA = re.compile(r"^## Scheda gara — (.+)$", re.MULTILINE)
_RE_NUM = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def _num(s: str | None):
    if not s:
        return None
    m = _RE_NUM.search(s)
    return float(m.group(0).replace(",", ".")) if m else None


def _campo(blocco: str, etichetta: str) -> str:
    m = re.search(rf"^- {re.escape(etichetta)}\s*:\s*(.*)$", blocco, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _tabella_criteri(blocco: str) -> list[dict]:
    righe = []
    for line in blocco.splitlines():
        if not line.strip().startswith("|"):
            continue
        celle = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(celle) < 4 or celle[0].lower() == "criterio" or set(celle[0]) <= {"-", " "}:
            continue
        pmax, presi = _num(celle[2]), _num(celle[3])
        if not celle[0] or pmax is None or presi is None:
            continue
        righe.append({
            "criterio": celle[0],
            "tipo": "qualitativo" if "qual" in celle[1].lower() else "tabellare",
            "punti_max": pmax,
            "punti_presi": presi,
            "note": celle[4] if len(celle) > 4 else "",
        })
    return righe


def leggi_testo() -> str:
    return ARCHIVIO_PATH.read_text(encoding="utf-8") if ARCHIVIO_PATH.exists() else ""


def leggi_schede(percorso: Path = ARCHIVIO_PATH) -> list[dict]:
    testo = percorso.read_text(encoding="utf-8") if percorso.exists() else ""
    matches = list(_RE_SCHEDA.finditer(testo))
    schede = []
    for i, m in enumerate(matches):
        titolo = m.group(1).strip()
        if titolo.startswith("[") and titolo.endswith("]"):
            continue  # è il template vuoto
        fine = matches[i + 1].start() if i + 1 < len(matches) else len(testo)
        blocco = testo[m.end():fine]
        schede.append({
            "titolo": titolo,
            "ente": _campo(blocco, "Ente/stazione appaltante"),
            "anno": _campo(blocco, "Data / anno"),
            "base_asta": _num(_campo(blocco, "Importo a base d'asta")),
            "risultato": _campo(blocco, "Risultato"),
            "punteggio_nostro": _num(_campo(blocco, "Nostro punteggio totale")),
            "punteggio_vincitore": _num(_campo(blocco, "Punteggio del vincitore (se noto)")),
            "ribasso_nostro": _num(_campo(blocco, "Nostro ribasso offerto")),
            "ribasso_vincitore": _num(_campo(blocco, "Ribasso del vincitore (se noto)")),
            "criteri": _tabella_criteri(blocco),
            "blocco": blocco.strip(),
        })
    return schede


def scheda_markdown(d: dict) -> str:
    righe = "\n".join(
        f"| {r['criterio']} | {r['tipo']} | {r['punti_max']} | {r['punti_presi']} | {r.get('note', '')} |"
        for r in d.get("criteri", [])
    ) or "|  |  |  |  |  |"
    return f"""
---

## Scheda gara — {d['titolo']}

**Dati generali**
- Ente/stazione appaltante: {d.get('ente', '')}
- Oggetto: {d.get('oggetto', '')}
- Data / anno: {d.get('anno', '')}
- Importo a base d'asta: {d.get('base_asta', '')}
- Criterio di aggiudicazione: {d.get('criterio_aggiudicazione', 'OEPV')}
- Ripartizione punteggio: tecnico {d.get('punti_tecnico', '')} / economico {d.get('punti_economico', '')}
- Soglia di sbarramento tecnico (se presente): {d.get('soglia', '')}

**Esito** (!)
- Risultato: {d.get('risultato', '')}
- Nostro punteggio totale: {d.get('punteggio_nostro', '')}
- Punteggio del vincitore (se noto): {d.get('punteggio_vincitore', '')}
- Nostra posizione in graduatoria: {d.get('posizione', '')}
- Distacco dal vincitore e su cosa (tecnico o economico): {d.get('distacco', '')}

**Punteggi voce per voce** (!) — dal verbale di commissione

| Criterio | Tipo (tabellare/qualitativo) | Punti max | Punti presi | Note |
|----------|------------------------------|-----------|-------------|------|
{righe}

**Offerta economica**
- Nostro ribasso offerto: {d.get('ribasso_nostro', '')}
- Ribasso del vincitore (se noto): {d.get('ribasso_vincitore', '')}
- Meccanismo di attribuzione punti prezzo: {d.get('formula_prezzo', '')}

**Lezioni apprese** (!)
- Cosa ha funzionato / ci ha fatto prendere punti: {d.get('funzionato', '')}
- Dove abbiamo lasciato punti e perché: {d.get('persi', '')}
- Contenuti riutilizzabili in futuro (progetti di riferimento, migliorie, metodologie): {d.get('riutilizzabili', '')}
- Note sulla commissione / ente (severità, preferenze): {d.get('note_ente', '')}
"""


def aggiungi_scheda(d: dict) -> None:
    ARCHIVIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    testo = leggi_testo()
    with open(ARCHIVIO_PATH, "w", encoding="utf-8") as f:
        f.write(testo.rstrip() + "\n" + scheda_markdown(d))


def salva_testo(testo: str) -> None:
    ARCHIVIO_PATH.write_text(testo, encoding="utf-8")
