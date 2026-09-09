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
