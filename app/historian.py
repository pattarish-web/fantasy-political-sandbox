import json
import re

from app import db
from app.export_html import export_chapter, rebuild_index
from app.gemini_client import call_gemini


def clean_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _status_for(name: str) -> str:
    alive_names = {row[0] for row in db.get_alive_characters()}
    return "Alive" if name in alive_names else "Dead"


def run_historian() -> dict:
    row = db.get_latest_undrafted_drama()
    if not row:
        return {"message": "nothing to write"}

    round_num, location, p1, p2, dialogue, consequence = row
    p1_meta = db.get_character_spotlight(p1) or {}
    p2_meta = db.get_character_spotlight(p2) or {}
    p1_status = _status_for(p1)
    p2_status = _status_for(p2)

    prompt = f"""
    You are 'The Grand Historian', an epic high-fantasy novelist.
    Turn this raw simulation log into a beautifully written fantasy political novel chapter (ภาษาไทย).

    IMPORTANT: There is NO fixed protagonist in this world.
    Whoever feels sharper, more consequential, or more vivid in THIS encounter may take the spotlight.
    Prior chronicle appearances (not destiny): {p1}={p1_meta.get('appearances', 0)}, {p2}={p2_meta.get('appearances', 0)}.
    Do not force a permanent hero arc.

    Log (Round {round_num}):
    Location: {location}
    Characters: {p1} (status: {p1_status}, faction: {p1_meta.get('faction', '?')})
               and {p2} (status: {p2_status}, faction: {p2_meta.get('faction', '?')})
    Dialogue: {dialogue}
    Consequence: {consequence}

    Rules:
    - Write it as a complete Epic High-Fantasy Novel Chapter.
    - Describe the atmosphere of '{location}', ideological clashes, and mystical/technological power effects.
    - Use elegant, smooth literature-grade Thai language (นิยายแปลแฟนตาซีฟอร์มยักษ์).
    - Let prominence emerge from the scene; supporting figures may outshine famous names.
    - Return STRICT JSON: {{"title": "ชื่อตอนภาษาไทย", "body": "เนื้อหาทั้งตอน..."}}
    """

    try:
        result = None
        last_err = None
        for _ in range(3):
            try:
                text = call_gemini(prompt, as_json=True)
                result = clean_json_response(text)
                if "title" in result and "body" in result:
                    break
                last_err = ValueError("missing title/body")
                result = None
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                last_err = e
                result = None
        if result is None:
            return {"error": f"Invalid JSON from model: {last_err}"}

        title = str(result["title"]).strip()
        body = str(result["body"]).strip()
        db.save_chapter(round_num, title, body, location, p1, p2)
        chapter = db.get_chapter_by_round(round_num)
        export_chapter(chapter)
        rebuild_index(db.list_chapters())
        return {
            "title": title,
            "novel": body,
            "round_num": round_num,
        }
    except Exception as e:
        return {"error": str(e)}
