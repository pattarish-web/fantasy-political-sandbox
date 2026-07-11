"""Emergent character generation — no fixed protagonists."""

import json
import re

from app import db
from app.gemini_client import call_gemini

RANDOM_SPAWN_CHANCE = 0.25
DRAMA_SPAWN_CHANCE = 0.55


def clean_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _parse_character_payload(raw: str, existing: set[str]) -> dict | None:
    data = clean_json_response(raw)
    name = str(data.get("name", "")).strip()
    faction = str(data.get("faction", "")).strip()
    personality = str(data.get("personality", "")).strip()
    special_power = str(data.get("special_power", "")).strip()
    if not name or name in existing:
        return None
    if not faction or not personality or not special_power:
        return None
    return {
        "name": name,
        "faction": faction,
        "personality": personality,
        "special_power": special_power,
    }


def generate_character(*, context: str, existing_names: list[str] | None = None) -> dict | None:
    """Ask Gemini for one new character; insert into DB. Returns character dict or None."""
    existing = set(existing_names if existing_names is not None else db.list_character_names())
    avoid = ", ".join(sorted(existing)[:40])
    prompt = f"""
You create ONE new original character for a High-Fantasy Political Sandbox (Thai names OK).
No fixed protagonist — anyone can rise or fall.

Context for this birth:
{context}

Do NOT reuse these existing names: {avoid}

Return STRICT JSON only:
{{
  "name": "unique full name",
  "faction": "faction/race label",
  "personality": "1-2 Thai sentences of personality/role",
  "special_power": "[พลัง - short name] Thai description of the power"
}}
"""
    last_err = None
    for _ in range(3):
        try:
            raw = call_gemini(prompt, as_json=True)
            char = _parse_character_payload(raw, existing)
            if not char:
                last_err = ValueError("duplicate or incomplete character")
                continue
            ok = db.insert_character(
                char["name"],
                char["faction"],
                char["personality"],
                char["special_power"],
            )
            if not ok:
                existing.add(char["name"])
                last_err = ValueError("name collision on insert")
                continue
            return char
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            last_err = e
    return None
