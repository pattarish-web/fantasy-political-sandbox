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
    
    artifacts = db.get_all_artifacts()
    artifacts_str = "\n".join([f"- {a['name']} ({a['description']}) Owner: {a['owner_name']}" for a in artifacts]) if artifacts else "None"

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
    
    [World Artifacts & Relics]
    {artifacts_str}

    Task & Superpower Rules:
    1. Write a clever dialogue in Thai (3-5 lines). Focus on ideological clashes, secret power usage, or rare romantic sparks.
    2. **Elemental Synergy & Counters**: When characters fight, heavily consider how their powers counter each other (e.g. Fire vs Ice, Magic vs Tech). A weaker character can win if their power counters the enemy's or if their INT is much higher.
    3. **Power Awakening**: If a character survives a high-stakes, deadly drama (is_drama=1) or pushes beyond their limits, they can AWAKEN. If so, return a new upgraded power name and description in 'power_awakened'.
    4. **Artifacts**: Characters can discover new artifacts or steal existing ones from each other. If an artifact changes hands or is created, specify it in 'artifact_event'.
    5. **Event Snapshots**: Provide a VERY DETAILED english image generation prompt ('p1_snapshot_prompt' & 'p2_snapshot_prompt') describing how they look IN THIS EXACT SCENE. Mention their clothes, injuries, weapons, and environment. E.g., "1boy, injured knight, bloody armor, fiery background, intense look, anime style, masterpiece".
    6. **Relationship Evolution (v3.0)**: Based on this interaction, do they become Lovers, Nemesis, Master-Apprentice, or sworn allies? If so, output it in 'relationship_update'.
    7. **All-Out Faction War (v3.0)**: If these two are faction leaders and the clash is severe enough, one can declare an ALL-OUT WAR against the other faction. If so, output in 'war_declaration'.
    8. Determine the consequence (gain influence, flee, die, awaken, steal artifact, etc.). Make it logically follow.
    9. Evaluate if it contains high drama or death (is_drama = 1 or 0).
    10. If someone dies, output their name in 'character_killed', else null.
    11. If a character uses resurrection to revive someone from the Graveyard, output their name in 'character_resurrected'.
    12. If the world severely lacks fresh blood, set 'needs_new_character' to true and provide a 'new_character_concept'.

    Return response STRICTLY in valid JSON format:
    {{
        "dialogue": "p1: ... \\np2: ...",
        "consequence": "Description of what happened",
        "is_drama": 1,
        "character_killed": null,
        "character_resurrected": null,
        "needs_new_character": false,
        "new_character_concept": null,
        "power_awakened": null, /* or {{ "character_name": "...", "new_power": "[พลังใหม่] คำอธิบาย..." }} */
        "artifact_event": null, /* or {{ "type": "create"|"steal", "artifact_name": "...", "owner_name": "...", "description": "..." }} */
        "relationship_update": null, /* or {{ "type": "Lovers"|"Nemesis"|"Master-Apprentice"|"Allies", "reason": "..." }} */
        "war_declaration": null, /* or {{ "aggressor_faction": "...", "defender_faction": "...", "reason": "..." }} */
        "p1_snapshot_prompt": "english prompt for char 1 in this scene",
        "p2_snapshot_prompt": "english prompt for char 2 in this scene"
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
        
        # Check for awakenings
        awakened = result.get("power_awakened")
        if awakened and isinstance(awakened, dict):
            c_name = awakened.get("character_name")
            new_pow = awakened.get("new_power")
            if c_name and new_pow:
                db.update_character_power(c_name, new_pow)
                born.append(f"🌟 พลังตื่นรู้: {c_name} ได้รับพลังใหม่ '{new_pow}'!")

        # Check for artifact events
        art_event = result.get("artifact_event")
        if art_event and isinstance(art_event, dict):
            e_type = art_event.get("type")
            a_name = art_event.get("artifact_name")
            o_name = art_event.get("owner_name")
            a_desc = art_event.get("description", "")
            if a_name and o_name:
                if e_type == "create":
                    db.insert_or_update_artifact(a_name, a_desc, o_name)
                    born.append(f"⚔️ อาวุธใหม่ปรากฏ: '{a_name}' ถูกครอบครองโดย {o_name}")
                elif e_type == "steal":
                    db.transfer_artifact(a_name, o_name)
                    born.append(f"🎭 ขโมยอาวุธ: '{a_name}' ตกไปอยู่ในมือของ {o_name}!")

        if killed:
            db.update_character_status(killed, "Dead")
            result["death_notice"] = f"💀 บันทึกพงศาวดาร: {killed} สิ้นชีพแล้ว!"
            
        # Check for relationship evolution
        rel_update = result.get("relationship_update")
        if rel_update and isinstance(rel_update, dict):
            r_type = rel_update.get("type")
            r_reason = rel_update.get("reason", "")
            if r_type:
                db.update_relationship(p1_name, p2_name, r_type, r_reason)
                born.append(f"💖 สายสัมพันธ์ใหม่: {p1_name} และ {p2_name} กลายเป็น '{r_type}'!")
                
        # Check for faction wars
        war_dec = result.get("war_declaration")
        if war_dec and isinstance(war_dec, dict):
            aggressor = war_dec.get("aggressor_faction")
            defender = war_dec.get("defender_faction")
            w_reason = war_dec.get("reason", "")
            if aggressor and defender and aggressor != defender:
                db.declare_war(aggressor, defender, w_reason)
                born.append(f"⚔️ ประกาศสงคราม: ฝ่าย {aggressor} ประกาศสงครามทำลายล้างกับ {defender}!")
            
        resurrected = result.get("character_resurrected")
        if resurrected and resurrected in dead_chars:
            db.update_character_status(resurrected, "Alive")
            result["resurrection_notice"] = f"✨ ปาฏิหาริย์: {resurrected} ฟื้นคืนชีพจากความตาย!"
            
        # Record snapshots
        p1_snap = result.get("p1_snapshot_prompt")
        if p1_snap:
            desc = f"ฉากที่ {p1_name} ปะทะ {p2_name} ณ {location}"
            db.add_character_image_prompt(p1_name, p1_snap, desc)
            
        p2_snap = result.get("p2_snapshot_prompt")
        if p2_snap:
            desc = f"ฉากที่ {p2_name} ปะทะ {p1_name} ณ {location}"
            db.add_character_image_prompt(p2_name, p2_snap, desc)

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
