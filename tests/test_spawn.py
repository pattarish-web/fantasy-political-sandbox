import json

from app.spawn import _parse_character_payload
from app.character_data import status_label


def _payload(**overrides):
    value = {
        "name": "ตะวัน",
        "faction": "สภาแสง",
        "personality": "สุขุมและเด็ดขาด",
        "special_power": "ควบคุมแสง",
        "gender": "ชาย", "sexuality": "รักต่างเพศ", "race": "มนุษย์",
        "age": "34 ปี", "height": "175 ซม.", "weight": "70 กก.",
        "skin_color": "ผิวแทน", "skills": "การทูต", "weapon": "ดาบ",
        "class_wealth": "ชนชั้นสูง", "morality": "ยึดความยุติธรรม",
        "ambition": "สร้างสันติภาพ", "flaw": "ไว้ใจคนง่าย", "title": "นักปราชญ์",
        "image_prompt": "anime portrait",
        "str": 60, "int": 90, "cha": 95, "agi": 70,
    }
    value.update(overrides)
    return json.dumps(value, ensure_ascii=False)


def test_spawn_rejects_english_visible_profile_fields():
    assert _parse_character_payload(_payload(faction="Council of Luminaries"), set()) is None


def test_spawn_accepts_thai_visible_profile_fields():
    result = _parse_character_payload(_payload(), set())
    assert result["faction"] == "สภาแสง"


def test_status_values_are_rendered_in_thai():
    assert status_label("alive") == "มีชีวิต"
    assert status_label("DEAD") == "เสียชีวิต"
