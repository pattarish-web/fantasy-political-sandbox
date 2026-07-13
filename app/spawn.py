"""Emergent character generation — no fixed protagonists."""

import json
import re

from app import db
from app.character_data import normalize_meta
from app.llm_client import call_llm, clean_json_response
from app.schemas import CharacterSpawnResult

RANDOM_SPAWN_CHANCE = 0.25
DRAMA_SPAWN_CHANCE = 0.55

def _normalize_anime_prompt(prompt: str) -> str:
    cleaned = " ".join(str(prompt).split())
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if "anime" not in lowered:
        return f"anime style, japanese anime, {cleaned}"
    if "japanese" not in lowered:
        return f"japanese anime style, {cleaned}"
    return cleaned


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
    required_text_fields = ["gender", "sexuality", "race", "age", "height", "weight", "skin_color",
                            "skills", "weapon", "class_wealth", "morality", "ambition", "flaw", "title", "image_prompt"]
    for field in required_text_fields:
        val = str(data.get(field, "")).strip()
        if not val or val == "None":
            return None
        # Profile prose is published directly to the Thai chronicle. Reject
        # accidental English output so the retry can produce a translated profile.
        if field != "image_prompt" and re.search(r"[A-Za-z]", val):
            return None
        meta[field] = _normalize_anime_prompt(val) if field == "image_prompt" else val

    for field in ["str", "int", "cha", "agi"]:
        try:
            val = int(data.get(field, 0))
            if not 1 <= val <= 100:
                return None
            meta[field] = val
        except (ValueError, TypeError):
            return None

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
        "meta_data": json.dumps(normalize_meta(meta, name), ensure_ascii=False)
    }


def generate_character(*, context: str, existing_names: list[str] | None = None) -> dict | None:
    """Ask Gemini for one new character; insert into DB. Returns character dict or None."""
    existing = set(existing_names if existing_names is not None else db.list_character_names())
    avoid = ", ".join(sorted(existing)[:40])
    prompt = f"""
You create ONE new original character for a High-Fantasy Political Sandbox.
Write EVERY visible field in natural Thai language only (แปล faction, personality,
power, biography, title, skills, weapon, morality, ambition and flaw). English is
allowed only inside image_prompt when needed for image generation. The character
name may be Thai or a transliterated proper name.
No fixed protagonist — anyone can rise or fall.

Context for this birth:
{context}

Do NOT reuse these existing names: {avoid}

Return STRICT JSON matching the exact schema requested.
"""
    last_err = None
    for _ in range(3):
        try:
            raw = call_llm(prompt, response_schema=CharacterSpawnResult)
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
