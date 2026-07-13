from app.continuity import validate_event_continuity


def test_new_race_requires_foreshadowing():
    errors = validate_event_continuity({"new_race": "เผ่าเงา"}, known_races={"มนุษย์"})
    assert "เผ่าใหม่ยังไม่มีเบาะแสหรือเหตุการณ์ปูพื้น" in errors


def test_new_race_with_foreshadowing_is_allowed():
    assert validate_event_continuity(
        {"new_race": "เผ่าเงา", "foreshadowing": "พบรอยเท้าที่ไม่ใช่มนุษย์"},
        known_races={"มนุษย์"},
    ) == []


def test_future_knowledge_is_rejected():
    errors = validate_event_continuity(
        {"requires_knowledge": ["แผนลับ"], "known_facts": []}, known_races={"มนุษย์"}
    )
    assert "ตัวละครอ้างข้อมูลที่ยังไม่รู้" in errors
