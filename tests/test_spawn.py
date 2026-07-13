import json

import pytest

from app.schemas import CharacterSpawnResult
from app.spawn import _parse_character_payload


def _payload():
    return {
        "name": "ไอลิน", "faction": "สภาเมฆา", "personality": "สุขุม", "special_power": "ผนึกสายลม",
        "gender": "female", "sexuality": "Heterosexual", "str": 60, "int": 70, "cha": 55, "agi": 80,
        "race": "มนุษย์", "age": "26 ปี", "height": "170cm", "weight": "60kg", "skin_color": "ผิวแทน",
        "skills": "เวทลม", "weapon": "หอกเงิน", "class_wealth": "ขุนนาง", "morality": "ยุติธรรม",
        "ambition": "รวมสภา", "flaw": "ใจร้อน", "title": "ผู้คุมพายุ", "image_prompt": "anime portrait",
    }


def test_spawn_parser_rejects_missing_profile_field():
    payload = _payload()
    del payload["race"]

    assert _parse_character_payload(json.dumps(payload), set()) is None


def test_spawn_schema_requires_profile_and_stat_fields():
    payload = _payload()
    del payload["weapon"]

    with pytest.raises(Exception):
        CharacterSpawnResult(**payload)


def test_spawn_parser_returns_complete_normalized_metadata():
    result = _parse_character_payload(json.dumps(_payload()), set())

    assert result is not None
    meta = json.loads(result["meta_data"])
    assert meta["gender"] == "หญิง"
    assert meta["height"] == "170 ซม."
    assert meta["weight"] == "60 กก."
    assert all(meta[field] for field in ("race", "skills", "weapon", "ambition", "flaw", "image_prompt"))
