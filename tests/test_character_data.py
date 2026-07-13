import json

from app.character_data import (
    PROFILE_FIELDS,
    canonicalize_character_name,
    normalize_display_value,
    normalize_meta,
)


def test_normalize_display_value_translates_visible_english_but_not_image_prompt():
    assert normalize_display_value("gender", "female") == "หญิง"
    assert normalize_display_value("sexuality", "Heterosexual") == "เฮเทอโรเซ็กชวล"
    assert normalize_display_value("sexuality", "Homosexual") == "โฮโมเซ็กชวล"
    assert normalize_display_value("height", "180cm") == "180 ซม."
    assert normalize_display_value("weight", "75kg") == "75 กก."
    prompt = "anime style, 1woman"
    assert normalize_display_value("image_prompt", prompt) == prompt


def test_normalize_meta_backfills_known_legacy_character_and_all_profile_fields():
    meta = normalize_meta({"gender": "female", "str": 8}, "นราอำพัน")

    assert set(PROFILE_FIELDS).issubset(meta)
    assert meta["gender"] == "หญิง"
    assert meta["race"] == "มนุษย์"
    assert meta["skills"] != "ข้อมูลยังไม่ระบุ"
    assert meta["str"] == 8
    assert all(meta[field] for field in PROFILE_FIELDS)


def test_unknown_character_uses_explicit_thai_fallback_instead_of_empty_profile():
    meta = normalize_meta({}, "โนวา")

    assert all(meta[field] == "ข้อมูลยังไม่ระบุ" for field in PROFILE_FIELDS if field != "image_prompt")
    assert "image_prompt" not in meta


def test_canonicalize_character_name_repairs_historical_alias():
    assert canonicalize_character_name("นราอำพัน (Nara-Amphan)") == "นราอำพัน"
    assert canonicalize_character_name("นราอำพัน") == "นราอำพัน"
    assert canonicalize_character_name("แม่ทัพหญิงวาเลเรีย") == "แม่ทัพหญิงวาเลเรีย"
