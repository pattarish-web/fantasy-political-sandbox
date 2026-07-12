import json
import random
import re

from app import db
from app.gemini_client import call_gemini, clean_json_response
from app.seed_data import LOCATIONS
from app.spawn import DRAMA_SPAWN_CHANCE, RANDOM_SPAWN_CHANCE, generate_character
from app.export_html import export_updated_characters


def run_simulation_batch(batch_size: int = 5) -> dict:
    round_num_start = db.get_latest_round() + 1
    born: list[dict] = []
    
    alive_chars = db.get_alive_characters()
    if len(alive_chars) < 2:
        return {"error": "ตัวละครเหลือน้อยเกินไป ไม่สามารถจำลองโลกต่อได้", "born": born}
        
    # Pre-select encounters
    encounters = []
    for i in range(batch_size):
        if len(alive_chars) < 2: break
        p1, p2 = random.sample(alive_chars, 2)
        loc = random.choice(LOCATIONS)
        
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
            return "\n      ".join(lines)
            
        p1_meta = db.parse_meta_data(p1[5] if len(p1) > 5 else "{}")
        p2_meta = db.parse_meta_data(p2[5] if len(p2) > 5 else "{}")
        
        encounters.append({
            "idx": i+1,
            "round": round_num_start + i,
            "location": loc,
            "p1": p1, "p1_meta_str": format_meta(p1_meta),
            "p2": p2, "p2_meta_str": format_meta(p2_meta),
        })

    recent_global = db.get_recent_global_logs(3)
    global_context = "\n".join([f"- Round {r['round_num']}: {r['p1_name']} vs {r['p2_name']} -> {r['consequence']}" for r in recent_global]) if recent_global else "None"
    
    dead_chars = db.get_dead_characters()
    graveyard_context = ", ".join(dead_chars) if dead_chars else "None"
    
    artifacts = db.get_all_artifacts()
    artifacts_str = "\n".join([f"- {a['name']} ({a['description']}) Owner: {a['owner_name']}" for a in artifacts]) if artifacts else "None"

    # Build encounters prompt string
    encounters_str = ""
    for enc in encounters:
        p1 = enc["p1"]
        p2 = enc["p2"]
        encounters_str += f"""
    Encounter {enc['idx']} (Round {enc['round']}): At {enc['location']}
    Character 1: {p1[0]} | Faction: {p1[1]} | Power: {p1[3]}
    Prior apps: {p1[4]} | Context: {p1[2]}
      {enc['p1_meta_str']}
    
    Character 2: {p2[0]} | Faction: {p2[1]} | Power: {p2[3]}
    Prior apps: {p2[4]} | Context: {p2[2]}
      {enc['p2_meta_str']}
    -----------------------------------"""

    prompt = f"""
    You are a Simulation Engine for a High-Fantasy Political World.
    There is NO fixed protagonist. Whoever is present may rise in prominence.

    [Recent World Events]
    {global_context}
    
    [Graveyard (Dead Characters)]
    {graveyard_context}
    
    [World Artifacts & Relics]
    {artifacts_str}

    Here are {batch_size} sequential encounters. Process them in order.
    {encounters_str}

    CRITICAL RULE (Ghost Duels): If a character is killed in Encounter X, they CANNOT fight in any later Encounter (e.g. Encounter Y). 
    If a later encounter involves a dead character, the other character should just 'find their corpse' or 'find traces of a battle', or the encounter should just be skipped/invalidated.

    Task & Superpower Rules for EACH encounter:
    1. Write a short, clever dialogue in Thai (1-2 lines) or description.
    2. Consider Elemental Synergy & Counters.
    3. Power Awakening: Set 'power_awakened'.
    4. Artifacts: Set 'artifact_event' if artifacts are found/stolen.
    5. Event Snapshots: Provide brief english image generation prompts ('p1_snapshot_prompt' & 'p2_snapshot_prompt'). Keep them very short (1 sentence).
    6. Relationship Evolution: Set 'relationship_update'.
    7. Faction War: Set 'war_declaration'.
    8. Determine the consequence.
    9. If high drama/death, is_drama = 1 else 0.
    10. If someone dies, 'character_killed' = name.
    11. If resurrected, 'character_resurrected' = name.

    Return response STRICTLY in valid JSON format as an ARRAY of exactly {batch_size} objects.
    [
      {{
        "encounter_idx": 1,
        "dialogue": "...",
        "consequence": "...",
        "is_drama": 1,
        "character_killed": null,
        "character_resurrected": null,
        "power_awakened": null,
        "artifact_event": null,
        "relationship_update": null,
        "war_declaration": null,
        "p1_snapshot_prompt": "...",
        "p2_snapshot_prompt": "..."
      }},
      ...
    ]
    """

    try:
        result_array = None
        last_err = None
        for _ in range(3):
            try:
                response_text = call_gemini(prompt, as_json=True)
                result_array = clean_json_response(response_text)
                if isinstance(result_array, list) and len(result_array) == batch_size:
                    break
            except Exception as e:
                last_err = e
        if not isinstance(result_array, list):
            return {"error": f"Invalid JSON array from model: {last_err}", "born": born}

        all_updated_chars = set()

        for idx, enc in enumerate(encounters):
            result = result_array[idx]
            
            p1_name = enc["p1"][0]
            p2_name = enc["p2"][0]
            location = enc["location"]
            r_num = enc["round"]
            
            all_updated_chars.add(p1_name)
            all_updated_chars.add(p2_name)
            
            is_drama = 1 if str(result.get("is_drama", "0")) == "1" else 0
            db.save_log(
                r_num,
                location,
                p1_name,
                p2_name,
                result.get("dialogue", ""),
                result.get("consequence", ""),
                is_drama,
            )

            # Re-fetch dead_chars in case someone died in earlier batch item
            dead_chars = db.get_dead_characters()

            killed = result.get("character_killed")
            if killed:
                db.update_character_status(killed, "Dead")
                
            awakened = result.get("power_awakened")
            if awakened and isinstance(awakened, dict):
                c_name = awakened.get("character_name")
                new_pow = awakened.get("new_power")
                if c_name and new_pow:
                    db.update_character_power(c_name, new_pow)

            art_event = result.get("artifact_event")
            if art_event and isinstance(art_event, dict):
                e_type = art_event.get("type")
                a_name = art_event.get("artifact_name")
                o_name = art_event.get("owner_name")
                a_desc = art_event.get("description", "")
                if a_name and o_name:
                    if e_type == "create":
                        db.insert_or_update_artifact(a_name, a_desc, o_name)
                    elif e_type == "steal":
                        db.transfer_artifact(a_name, o_name)

            rel_update = result.get("relationship_update")
            if rel_update and isinstance(rel_update, dict):
                r_type = rel_update.get("type")
                r_reason = rel_update.get("reason", "")
                if r_type:
                    db.update_relationship(p1_name, p2_name, r_type, r_reason)

            war_dec = result.get("war_declaration")
            if war_dec and isinstance(war_dec, dict):
                aggressor = war_dec.get("aggressor_faction")
                defender = war_dec.get("defender_faction")
                w_reason = war_dec.get("reason", "")
                if aggressor and defender and aggressor != defender:
                    db.declare_war(aggressor, defender, w_reason)

            resurrected = result.get("character_resurrected")
            if resurrected and resurrected in dead_chars:
                db.update_character_status(resurrected, "Alive")

            p1_snap = result.get("p1_snapshot_prompt")
            if p1_snap:
                desc = f"ฉากที่ {p1_name} ปะทะ {p2_name} ณ {location}"
                db.add_character_image_prompt(p1_name, p1_snap, desc)
                
            p2_snap = result.get("p2_snapshot_prompt")
            if p2_snap:
                desc = f"ฉากที่ {p2_name} ปะทะ {p1_name} ณ {location}"
                db.add_character_image_prompt(p2_name, p2_snap, desc)

        # Random spawn at the end of batch (or once per round)
        for enc in encounters:
            if random.random() < RANDOM_SPAWN_CHANCE:
                try:
                    char = generate_character(
                        context=f"Round {enc['round']}: a new figure enters the political stage."
                    )
                    if char:
                        born.append({**char, "reason": "random"})
                        all_updated_chars.add(char["name"])
                except Exception:
                    pass

        try:
            export_updated_characters(list(all_updated_chars))
        except Exception as e:
            print(f"Failed to export profiles: {e}")

        return {"status": "batch_completed", "events_processed": batch_size, "born": born}

    except Exception as e:
        return {"error": str(e), "born": born}
