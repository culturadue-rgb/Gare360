"""
Assistente AI "stratega-gare".

Il prompt di sistema vive in prompts/stratega_gare.md (per ora un placeholder:
lo riempiremo dopo). All'avvio di ogni risposta viene arricchito con il
contenuto dell'archivio storico e del tracker, così l'assistente ragiona sui
dati reali dell'azienda.

Richiede la variabile d'ambiente ANTHROPIC_API_KEY (o il campo nella sidebar).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PROMPT_PATH = Path(__file__).parent / "prompts" / "stratega_gare.md"
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


def rispondi(messaggi: list[dict], system: str, api_key: str | None = None,
             modello: str = MODELLO_DEFAULT) -> str:
    """messaggi: lista di {"role": "user"|"assistant", "content": str}."""
    try:
        import anthropic
    except ImportError:
        return "Manca la libreria `anthropic`: esegui `pip install anthropic`."

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return ("Nessuna chiave API configurata. Inseriscila nella barra laterale "
                "oppure imposta la variabile d'ambiente ANTHROPIC_API_KEY.")

    client = anthropic.Anthropic(api_key=key)
    try:
        resp = client.messages.create(
            model=modello,
            max_tokens=2000,
            system=system,
            messages=messaggi,
        )
    except Exception as e:  # noqa: BLE001
        return f"Errore nella chiamata al modello: {e}"
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
