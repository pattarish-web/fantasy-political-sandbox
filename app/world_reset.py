"""World reset with AI-generated fresh characters."""

from app import db
from app.export_html import clear_exported_content, export_all_characters, rebuild_index


# The 8 factions that must be represented in every fresh world.
FACTIONS = [
    "สภาผู้สำเร็จราชการ",
    "กองทัพชายแดน",
    "ศาสนจักรแห่งคำสัตย์",
    "สมาพันธ์พ่อค้า",
    "เครือข่ายใต้ดิน",
    "ชุมชนลุ่มน้ำ",
    "ราชสำนักเก่า",
    "กองกำลังอิสระ",
]


def _generate_fresh_cast() -> bool:
    """Try to generate 8 new AI characters, one per faction. Returns True on success."""
    from app.spawn import generate_character

    created = 0
    for faction in FACTIONS:
        context = (
            f"The world has just been reborn. You must create a character for the "
            f"'{faction}' faction. Give them a unique Thai-phonetic fantasy name, "
            f"a vivid personality with clear political stance, a private desire, "
            f"a fear, and an emotional wound. Make their goal specific and tied to "
            f"the faction's role in the power struggle."
        )
        try:
            char = generate_character(context=context)
            if char:
                created += 1
                print(f"   ✨ สร้างตัวละครใหม่: {char['name']} ({faction})")
            else:
                print(f"   ⚠️ สร้างตัวละครสำหรับ {faction} ไม่สำเร็จ")
        except Exception as e:
            print(f"   ❌ ข้อผิดพลาดในการสร้างตัวละคร {faction}: {e}")

    print(f"\n   📊 สร้างตัวละครใหม่สำเร็จ {created}/{len(FACTIONS)} คน")
    return created == len(FACTIONS)


def reset_world() -> dict:
    import random

    summary = db.reset_world_state()

    # Randomize image seed salt for fresh portraits
    state = db.get_story_state()
    state["image_seed_salt"] = random.randint(1, 999999)
    db.save_story_state(state)

    # Try AI-generated characters; if it fails, keep the seeded fallback cast
    try:
        print("\n🎲 กำลังสุ่มสร้างตัวละครใหม่ด้วย AI...")
        # Delete the fallback seed characters first
        with db._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM characters")
            conn.commit()

        success = _generate_fresh_cast()
        if not success:
            # If AI generation partially failed, re-seed fallback for missing slots
            remaining = db.list_character_names()
            if len(remaining) < 4:
                print("   🔄 AI สร้างได้น้อยเกินไป กำลังเติมตัวละครสำรอง...")
                from app.seed_data_new import INITIAL_CHARACTERS
                with db._connect() as conn:
                    cur = conn.cursor()
                    for char in INITIAL_CHARACTERS:
                        cur.execute(
                            "INSERT OR IGNORE INTO characters "
                            "(name, faction, personality, special_power, status, appearances, meta_data) "
                            "VALUES (?, ?, ?, ?, ?, 0, ?)",
                            char,
                        )
                    conn.commit()
    except Exception as e:
        print(f"   ❌ การสุ่มสร้าง AI ล้มเหลว กำลังใช้ตัวละครสำรอง: {e}")
        # Re-seed fallback characters
        from app.seed_data_new import INITIAL_CHARACTERS
        with db._connect() as conn:
            cur = conn.cursor()
            for char in INITIAL_CHARACTERS:
                cur.execute(
                    "INSERT OR IGNORE INTO characters "
                    "(name, faction, personality, special_power, status, appearances, meta_data) "
                    "VALUES (?, ?, ?, ?, ?, 0, ?)",
                    char,
                )
            conn.commit()

    # Update character count in summary
    summary["characters"] = len(db.list_character_names())

    clear_exported_content()
    export_all_characters()

    # Run 10 rounds of simulation automatically
    try:
        print("\n🔮 กำลังรันจำลองโลกเริ่มต้น 10 รอบ...")
        from app.simulation import run_simulation_batch
        sim_result = run_simulation_batch(10)
        summary["simulation_result"] = sim_result
        print("   ✅ รันจำลองโลกเริ่มต้น 10 รอบสำเร็จ")
    except Exception as sim_err:
        print(f"   ❌ ไม่สามารถรันจำลองโลกได้: {sim_err}")

    rebuild_index(db.list_chapters())
    return summary
