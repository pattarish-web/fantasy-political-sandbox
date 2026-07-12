"""Emergent character generation — no fixed protagonists."""

import json

from app import db
from app.gemini_client import call_gemini, clean_json_response
from app.schemas import CharacterSpawnResult

RANDOM_SPAWN_CHANCE = 0.25
DRAMA_SPAWN_CHANCE = 0.55


def _parse_character_payload(raw: str, existing: set[str]) -> dict | None:
    try:
        data = json.loads(raw)
    except Exception:
        data = clean_json_response(raw)
        
    name = str(data.get("name", "")).strip()
    faction = str(data.get("faction", "")).strip()
    personality = str(data.get("personality", "")).strip()
    special_power = str(data.get("special_power", "")).strip()
    
    if not name or name in existing:
        return None
    if not faction or not personality or not special_power:
        return None
        
    meta = {}
    
    # Text Fields
    for field in ["gender", "sexuality", "race", "age", "height", "weight", "skin_color", 
                  "skills", "weapon", "class_wealth", "morality", "ambition", "flaw", "title"]:
        val = str(data.get(field, "")).strip()
        if val and val != "None":
            meta[field] = val
            
    # Number Fields
    for field in ["str", "int", "cha", "agi"]:
        try:
            val = int(data.get(field, 0))
            if val > 0:
                meta[field] = val
        except (ValueError, TypeError):
            pass

    # Relationships
    rel_target = data.get("relationship_target")
    rel_type = data.get("relationship_type")
    if rel_target and str(rel_target).strip() and str(rel_target).strip() not in ("null", "None"):
        meta["relationship_target"] = str(rel_target).strip()
        meta["relationship_type"] = str(rel_type).strip() if rel_type else "เกี่ยวข้อง"

    return {
        "name": name,
        "faction": faction,
        "personality": personality,
        "special_power": special_power,
        "meta_data": json.dumps(meta, ensure_ascii=False) if meta else "{}"
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

Return STRICT JSON matching the exact schema requested.
"""
    last_err = None
    for _ in range(3):
        try:
            raw = call_gemini(prompt, response_schema=CharacterSpawnResult)
            char = _parse_character_payload(raw, existing)
            if not char:
                last_err = ValueError("duplicate or incomplete character")
                continue
            ok = db.insert_character(
                char["name"],
                char["faction"],
                char["personality"],
                char["special_power"],
                "Alive",
                char["meta_data"]
            )
            if not ok:
                existing.add(char["name"])
                last_err = ValueError("name collision on insert")
                continue
            return char
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            last_err = e
    return None
