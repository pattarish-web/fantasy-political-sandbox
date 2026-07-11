import json
import random
import re

from app.gemini_client import call_gemini
from app.seed_data import LOCATIONS
from app import db


def clean_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def run_simulation_round(round_number: int | None = None) -> dict:
    round_num = round_number if round_number else db.get_latest_round() + 1
    alive_chars = db.get_alive_characters()

    if len(alive_chars) < 2:
        return {"error": "ตัวละครเหลือน้อยเกินไป ไม่สามารถจำลองโลกต่อได้"}

    p1, p2 = random.sample(alive_chars, 2)
    location = random.choice(LOCATIONS)
    p1_name, p1_faction, p1_person, p1_power = p1
    p2_name, p2_faction, p2_person, p2_power = p2

    prompt = f"""
    You are a Simulation Engine for a High-Fantasy Political World rich in diverse races, technologies, faiths, and unique traits.
    Two AI Agents have run into each other at '{location}'.

    Character 1: {p1_name} | Faction: {p1_faction} | Power: {p1_power} | Context: {p1_person}
    Character 2: {p2_name} | Faction: {p2_faction} | Power: {p2_power} | Context: {p2_person}

    Task:
    1. Write a clever dialogue in Thai (3-5 lines). Show ideological clashes or secret power usage.
    2. Determine the consequence.
    3. Evaluate if it contains high drama or death (is_drama = 1 or 0).
    4. If someone dies, output their name in 'character_killed', else null.

    Return response STRICTLY in valid JSON format:
    {{
        "dialogue": "p1: ... \\np2: ...",
        "consequence": "Description of what happened",
        "is_drama": 1,
        "character_killed": null
    }}
    """

    try:
        result = None
        last_err = None
        for _ in range(3):
            try:
                response_text = call_gemini(prompt, as_json=True)
                result = clean_json_response(response_text)
                break
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                last_err = e
        if result is None:
            return {"error": f"Invalid JSON from model: {last_err}"}

        is_drama = 1 if str(result.get("is_drama", "0")) == "1" else 0
        db.save_log(
            round_num,
            location,
            p1_name,
            p2_name,
            result.get("dialogue", ""),
            result.get("consequence", ""),
            is_drama,
        )

        killed = result.get("character_killed")
        if killed and killed in [p1_name, p2_name]:
            db.update_character_status(killed, "Dead")
            result["death_notice"] = f"💀 บันทึกพงศาวดาร: {killed} สิ้นชีพแล้ว!"

        result["is_drama"] = is_drama
        result["round_num"] = round_num
        result["location"] = location
        result["chars"] = f"{p1_name} VS {p2_name}"
        return result
    except Exception as e:
        return {"error": str(e)}
