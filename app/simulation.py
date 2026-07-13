import json
import random

from app import db
from app.llm_client import call_llm, clean_json_response
from app.seed_data import LOCATIONS
from app.spawn import DRAMA_SPAWN_CHANCE, RANDOM_SPAWN_CHANCE, generate_character
from app.export_html import export_updated_characters
from app.schemas import SimulationBatchResult


def _is_major_visual_event(enc: dict) -> bool:
    if enc.get("character_killed"):
        return True
    if enc.get("power_awakened"):
        return True
    if enc.get("artifact_event"):
        return True
    if enc.get("war_declaration"):
        return True
    return False


def _record_visual_prompt(name: str, prompt: str, description: str) -> None:
    if not prompt:
        return
    db.add_character_image_prompt(name, prompt, description)


def _fallback_visual_prompt(name: str, reason: str = "") -> str:
    character = db.get_character(name)
    if character:
        meta = db.parse_meta_data(character.get("meta_data"))
        prompts = meta.get("image_prompts", [])
        if prompts:
            latest = prompts[-1].get("prompt")
            if latest:
                return latest
        base_prompt = meta.get("image_prompt")
        if base_prompt:
            return base_prompt
    suffix = f", {reason}" if reason else ""
    return f"anime style, japanese anime, portrait, dramatic lighting{suffix}"


def _validate_encounters(encounters: list[dict], alive_names: set[str]) -> str | None:
    planned_dead: set[str] = set()
    for encounter in encounters:
        if not isinstance(encounter, dict):
            return "Each encounter must be an object"
        if "character_resurrected" in encounter:
            return "Resurrection is not supported"
        p1_name = encounter.get("p1_name")
        p2_name = encounter.get("p2_name")
        available_names = alive_names - planned_dead
        if (
            not isinstance(p1_name, str)
            or not isinstance(p2_name, str)
            or p1_name == p2_name
            or p1_name not in available_names
            or p2_name not in available_names
        ):
            return "Encounter participants must be distinct known living characters"
        killed = encounter.get("character_killed")
        if killed is not None and (
            not isinstance(killed, str) or killed not in {p1_name, p2_name}
        ):
            return "A declared death must be one of the encounter participants"
        if killed:
            planned_dead.add(killed)
    return None


def _story_facts(encounter: dict) -> dict:
    return {
        "character_killed": encounter.get("character_killed"),
        "power_awakened": encounter.get("power_awakened"),
        "relationship_update": encounter.get("relationship_update"),
        "artifact_event": encounter.get("artifact_event"),
        "war_declaration": encounter.get("war_declaration"),
        "consequence": encounter.get("consequence", ""),
    }


def run_simulation_batch(batch_size: int = 5) -> dict:
    print(f"\\n--- 🔮 เริ่มต้นการจำลองโลก (จำนวน {batch_size} เหตุการณ์) ---")
    round_num_start = db.get_latest_round() + 1
    born: list[dict] = []
    
    alive_chars = db.get_alive_characters()
    print(f"👥 จำนวนตัวละครที่ยังมีชีวิตในระบบ: {len(alive_chars)} คน")
    if len(alive_chars) < 2:
        print("❌ เกิดข้อผิดพลาด: ตัวละครเหลือน้อยเกินไป ไม่สามารถจำลองโลกต่อได้")
        return {"error": "ตัวละครเหลือน้อยเกินไป ไม่สามารถจำลองโลกต่อได้", "born": born}
        
    def format_meta(meta_str):
        meta = db.parse_meta_data(meta_str)
        if not meta: return "None"
        lines = []
        if 'str' in meta: lines.append(f"STR {meta.get('str')}, INT {meta.get('int')}, CHA {meta.get('cha')}")
        if 'race' in meta: lines.append(f"{meta.get('race')}")
        if 'skills' in meta: lines.append(f"Skills: {meta.get('skills')}")
        if 'weapon' in meta: lines.append(f"Weapon: {meta.get('weapon')}")
        return " / ".join(lines)
            
    chars_info = []
    for c in alive_chars:
        # c = (name, faction, personality, power, appearances, meta_data)
        name, faction, _, power, _, meta_str = c
        chars_info.append(f"- {name} (Faction: {faction}) | Power: {power} | {format_meta(meta_str)}")
        
    chars_context = "\n".join(chars_info)

    recent_global = db.get_recent_global_logs(5)
    global_context = "\n".join([f"- Round {r['round_num']}: {r['p1_name']} vs {r['p2_name']} -> {r['consequence']}" for r in recent_global]) if recent_global else "None"
    
    dead_chars = db.get_dead_characters()
    graveyard_context = ", ".join(dead_chars) if dead_chars else "None"
    
    artifacts = db.get_all_artifacts()
    artifacts_str = "\n".join([f"- {a['name']} ({a['description']}) Owner: {a['owner_name']}" for a in artifacts]) if artifacts else "None"

    locations_str = ", ".join(LOCATIONS)

    prompt = f"""
You are a Simulation Engine for a High-Fantasy Political World (Dungeon Master).
There is NO fixed protagonist. Whoever is present may rise in prominence.

[Recent World Events]
{global_context}

[Graveyard (Dead Characters)]
{graveyard_context}

[World Artifacts & Relics]
{artifacts_str}

[Locations Available]
{locations_str}

[Alive Characters Roster]
{chars_context}

YOUR TASK:
Generate exactly {batch_size} sequential encounters (events). 
For EACH encounter:
1. CHOOSE two DIFFERENT characters (p1_name, p2_name) from the Alive Roster who have a reason to interact, fight, or ally.
2. CRITICAL RULE (Ghost Duels): If a character dies in Encounter N, they CANNOT be chosen for Encounter N+1 or later. Keep track of deaths as you generate!
3. CHOOSE a location from the available list.
4. Write a short dialogue (Thai) and consequence.
5. If high drama or death occurs, set is_drama=1.

7. IMPORTANT for snapshots (p1_snapshot_prompt & p2_snapshot_prompt): Generate Stable Diffusion prompts that focus ONLY on their facial expression and upper body. DO NOT describe them fighting, holding weapons, or doing complex actions. (e.g. '1boy, angry face, looking at viewer, portrait, cinematic lighting')

Return the events in the structured JSON array format exactly as requested.
"""

    try:
        print("🧠 กำลังส่งข้อมูลให้ Dungeon Master (Groq) ตัดสินใจเหตุการณ์ทั้งหมด...")
        response_text = call_llm(prompt, response_schema=SimulationBatchResult)
        
        try:
            result_data = json.loads(response_text)
            print("✅ Gemini ตอบกลับมาในรูปแบบ JSON สำเร็จและสมบูรณ์")
        except Exception:
            print("⚠️ พบปัญหาในการแกะ JSON เล็กน้อย กำลังใช้ระบบ Fallback...")
            result_data = clean_json_response(response_text)
            
        encounters = result_data.get("encounters", [])
        print(f"📌 ได้รับข้อมูลทั้งหมด {len(encounters)} เหตุการณ์จาก AI")
        if len(encounters) != batch_size:
            print(f"❌ จำนวนเหตุการณ์ไม่ตรงตามที่ขอ (ได้มา {len(encounters)}/{batch_size})")
            return {"error": f"Model returned {len(encounters)} encounters instead of {batch_size}", "born": born}

        validation_error = _validate_encounters(
            encounters,
            {character[0] for character in alive_chars},
        )
        if validation_error:
            return {"error": validation_error, "born": born}

        all_updated_chars = set()

        for idx, enc in enumerate(encounters):
            p1_name = enc.get("p1_name", "Unknown")
            p2_name = enc.get("p2_name", "Unknown")
            location = enc.get("location", "Unknown")
            r_num = round_num_start + idx
            
            print(f"\\n   ⚔️ เหตุการณ์ที่ {idx+1} (รอบที่ {r_num}) ณ {location}")
            print(f"      {p1_name} พบกับ {p2_name}")
            print(f"      บทสนทนา: {enc.get('dialogue', '-')}")
            print(f"      ผลลัพธ์: {enc.get('consequence', '-')}")
            
            all_updated_chars.add(p1_name)
            all_updated_chars.add(p2_name)
            
            is_drama = 1 if str(enc.get("is_drama", "0")) == "1" else 0
            killed = enc.get("character_killed")
            db.save_log(
                r_num,
                location,
                p1_name,
                p2_name,
                enc.get("dialogue", ""),
                enc.get("consequence", ""),
                is_drama,
                _story_facts(enc),
            )

            if killed:
                print(f"      💀 ฆาตกรรม: {killed} ถูกสังหาร!")
                db.update_character_status(killed, "Dead")
                
            awakened = enc.get("power_awakened")
            if awakened and isinstance(awakened, dict):
                c_name = awakened.get("character_name")
                new_pow = awakened.get("new_power")
                if c_name and new_pow:
                    print(f"      ✨ พลังตื่นรู้: {c_name} ได้รับพลัง '{new_pow}'")
                    db.update_character_power(c_name, new_pow)

            art_event = enc.get("artifact_event")
            if art_event and isinstance(art_event, dict):
                e_type = art_event.get("type")
                a_name = art_event.get("artifact_name")
                o_name = art_event.get("owner_name")
                a_desc = art_event.get("description", "")
                if a_name and o_name:
                    if e_type == "create":
                        print(f"      🛡️ สมบัติใหม่: {o_name} ค้นพบ '{a_name}'")
                        db.insert_or_update_artifact(a_name, a_desc, o_name)
                    elif e_type == "steal":
                        print(f"      🗡️ ปล้นชิง: {o_name} แย่งชิง '{a_name}' มาได้!")
                        db.transfer_artifact(a_name, o_name)

            rel_update = enc.get("relationship_update")
            if rel_update and isinstance(rel_update, dict):
                r_type = rel_update.get("type")
                r_reason = rel_update.get("reason", "")
                if r_type:
                    print(f"      🤝 ความสัมพันธ์: {p1_name} และ {p2_name} เปลี่ยนเป็น '{r_type}'")
                    db.update_relationship(p1_name, p2_name, r_type, r_reason)

            war_dec = enc.get("war_declaration")
            if war_dec and isinstance(war_dec, dict):
                aggressor = war_dec.get("aggressor_faction")
                defender = war_dec.get("defender_faction")
                w_reason = war_dec.get("reason", "")
                if aggressor and defender and aggressor != defender:
                    print(f"      🔥 สงคราม: {aggressor} ประกาศสงครามกับ {defender}!")
                    db.declare_war(aggressor, defender, w_reason)

            if _is_major_visual_event(enc):
                major_desc = f"เหตุการณ์สำคัญรอบ {r_num}: {enc.get('consequence', '')}".strip()
                p1_snap = enc.get("p1_snapshot_prompt") or _fallback_visual_prompt(p1_name, major_desc)
                _record_visual_prompt(p1_name, p1_snap, major_desc or f"เหตุการณ์สำคัญรอบ {r_num}")

                p2_snap = enc.get("p2_snapshot_prompt") or _fallback_visual_prompt(p2_name, major_desc)
                _record_visual_prompt(p2_name, p2_snap, major_desc or f"เหตุการณ์สำคัญรอบ {r_num}")

        if random.random() < RANDOM_SPAWN_CHANCE:
            try:
                char = generate_character(context=f"Round {round_num_start}: a new figure enters the political stage.")
                if char:
                    print(f"\\n   🌱 กำเนิดตัวละครใหม่แบบสุ่ม: {char['name']} (ฝักใฝ่ {char['faction']})")
                    born.append({**char, "reason": "random"})
                    all_updated_chars.add(char["name"])
            except Exception:
                pass

        try:
            print(f"\\n📦 กำลังส่งออกข้อมูลโปรไฟล์ตัวละครที่อัปเดตทั้งหมด {len(all_updated_chars)} คน...")
            export_updated_characters(list(all_updated_chars))
        except Exception as e:
            print(f"❌ พบข้อผิดพลาดในการ Export โปรไฟล์: {e}")

        print("🎉 สิ้นสุดการจำลองโลกใน Batch นี้อย่างสมบูรณ์!\\n")
        return {"status": "batch_completed", "events_processed": batch_size, "born": born}

    except Exception as e:
        print(f"\\n🚨 ค้นพบข้อผิดพลาดร้ายแรงระหว่างจำลองเหตุการณ์: {e}")
        return {"error": str(e), "born": born}
