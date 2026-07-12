import json
import random
import re

from app import db
from app.gemini_client import call_gemini
from app.seed_data import LOCATIONS
from app.spawn import DRAMA_SPAWN_CHANCE, RANDOM_SPAWN_CHANCE, generate_character


def clean_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def run_simulation_round(round_number: int | None = None) -> dict:
    round_num = round_number if round_number else db.get_latest_round() + 1
    born: list[dict] = []

    # Continuous world growth: chance to birth a wanderer each round
    if random.random() < RANDOM_SPAWN_CHANCE:
        try:
            char = generate_character(
                context=f"Round {round_num}: a new figure enters the political stage unprompted."
            )
            if char:
                born.append({**char, "reason": "random"})
        except Exception:
            pass  # spawn is optional; main simulation continues

    alive_chars = db.get_alive_characters()
    if len(alive_chars) < 2:
        return {"error": "ตัวละครเหลือน้อยเกินไป ไม่สามารถจำลองโลกต่อได้", "born": born}

    p1, p2 = random.sample(alive_chars, 2)
    location = random.choice(LOCATIONS)
    p1_name, p1_faction, p1_person, p1_power = p1[:4]
    p2_name, p2_faction, p2_person, p2_power = p2[:4]
    p1_apps = p1[4] if len(p1) > 4 else 0
    p2_apps = p2[4] if len(p2) > 4 else 0
    
    # Parse meta_data if available
    def parse_meta(meta_str):
        try:
            return json.loads(meta_str) if meta_str else {}
        except:
            return {}
            
    p1_meta = parse_meta(p1[5] if len(p1) > 5 else "{}")
    p2_meta = parse_meta(p2[5] if len(p2) > 5 else "{}")
    
    # Format metadata for prompt
    def format_meta(meta):
        if not meta: return "None"
        lines = []
        if 'str' in meta: lines.append(f"Stats: STR {meta.get('str')}, INT {meta.get('int')}, CHA {meta.get('cha')}, AGI {meta.get('agi')}")
        if 'race' in meta: lines.append(f"Physical: {meta.get('race')} / Age: {meta.get('age')} / {meta.get('height')} / {meta.get('weight')}")
        if 'skills' in meta: lines.append(f"Skills: {meta.get('skills')}")
        if 'weapon' in meta: lines.append(f"Weapon: {meta.get('weapon')}")
        if 'title' in meta: lines.append(f"Title: {meta.get('title')}")
        if 'ambition' in meta: lines.append(f"Ambition: {meta.get('ambition')}")
        if 'flaw' in meta: lines.append(f"Flaw: {meta.get('flaw')}")
        if 'class_wealth' in meta: lines.append(f"Status: {meta.get('class_wealth')} / Morality: {meta.get('morality')}")
        return "\n    ".join(lines)
        
    p1_meta_str = format_meta(p1_meta)
    p2_meta_str = format_meta(p2_meta)
    
    recent_global = db.get_recent_global_logs(3)
    global_context = "\n".join([f"- Round {r['round_num']}: {r['p1_name']} vs {r['p2_name']} -> {r['consequence']}" for r in recent_global]) if recent_global else "None"
    
    p1_history = db.get_character_logs(p1_name)
    p1_context = "\n".join([f"- Round {r['round_num']}: {r['consequence']}" for r in p1_history]) if p1_history else "None"
    
    p2_history = db.get_character_logs(p2_name)
    p2_context = "\n".join([f"- Round {r['round_num']}: {r['consequence']}" for r in p2_history]) if p2_history else "None"

    dead_chars = db.get_dead_characters()
    graveyard_context = ", ".join(dead_chars) if dead_chars else "None"

    prompt = f"""
    You are a Simulation Engine for a High-Fantasy Political World.
    There is NO fixed protagonist. Whoever is present may rise in prominence.

    Two figures meet at '{location}'.
    Character 1: {p1_name} | Faction: {p1_faction} | Power: {p1_power}
    Prior appearances in chronicles: {p1_apps} | Context: {p1_person}
    {p1_meta_str}
    Character 1's Recent History:
    {p1_context}
    
    Character 2: {p2_name} | Faction: {p2_faction} | Power: {p2_power}
    Prior appearances in chronicles: {p2_apps} | Context: {p2_person}
    {p2_meta_str}
    Character 2's Recent History:
    {p2_context}

    [Recent World Events]
    {global_context}
    
    [Graveyard (Dead Characters)]
    {graveyard_context}

    Task:
    1. Write a clever dialogue in Thai (3-5 lines). Focus heavily on ideological clashes or secret power usage. OCCASIONALLY (as a rare spice), show romantic sparks/seduction if their personalities and sexualities naturally align. Reference recent events or their past history if relevant.
    2. Determine the consequence (gain influence, lose face, flee, die, etc. Rarely: fall in love or form a political marriage). Make it logically follow the continuity of the world events.
    3. Evaluate if it contains high drama or death (is_drama = 1 or 0).
    4. If someone dies, output their name in 'character_killed', else null.
    5. If a character has resurrection/necromancy power and decides to revive someone from the Graveyard, output their name in 'character_resurrected', else null.
    6. If the current world events severely lack fresh blood or a specific type of new power/faction is needed to balance the world, set 'needs_new_character' to true and provide a 'new_character_concept' (e.g. "A mysterious mercenary seeking revenge for round 5"). Otherwise false/null.
    Do not crown a permanent hero — let this encounter decide who feels sharper this round.

    Return response STRICTLY in valid JSON format:
    {{
        "dialogue": "p1: ... \\np2: ...",
        "consequence": "Description of what happened",
        "is_drama": 1,
        "character_killed": null,
        "character_resurrected": null,
        "needs_new_character": false,
        "new_character_concept": null
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
            return {"error": f"Invalid JSON from model: {last_err}", "born": born}

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
            
        resurrected = result.get("character_resurrected")
        if resurrected and resurrected in dead_chars:
            db.update_character_status(resurrected, "Alive")
            result["resurrect_notice"] = f"✨ ปาฏิหาริย์เกิดขึ้น: {resurrected} ฟื้นคืนชีพจากความตาย!"

        if result.get("needs_new_character") and result.get("new_character_concept"):
            try:
                related = generate_character(
                    context=f"The world needs a new figure. Concept requested by AI: {result.get('new_character_concept')}"
                )
                if related:
                    born.append({**related, "reason": "ai_request"})
            except Exception:
                pass

        result["is_drama"] = is_drama
        result["round_num"] = round_num
        result["location"] = location
        result["chars"] = f"{p1_name} VS {p2_name}"
        result["born"] = born
        if born:
            names = ", ".join(c["name"] for c in born)
            result["birth_notice"] = f"🌱 ตัวละครใหม่เข้าสู่โลก: {names}"
        return result
    except Exception as e:
        return {"error": str(e), "born": born}
