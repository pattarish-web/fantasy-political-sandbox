from app.world_rules import normalize_fantasy_meta


def test_missing_fantasy_fields_get_safe_defaults():
    result = normalize_fantasy_meta({})
    assert result["race"] == "มนุษย์"
    assert result["magic_school"] == "ไม่มีเวท"
    assert result["element"] == "ไม่มีธาตุ"
    assert result["magic_cost"] == "ไม่มี"


def test_unknown_race_and_element_are_normalized():
    result = normalize_fantasy_meta({"race": "จักรกล", "element": "จักรวาล"})
    assert result["race"] == "มนุษย์"
    assert result["element"] == "ไม่มีธาตุ"


def test_magic_without_school_cannot_keep_cost_or_limit():
    result = normalize_fantasy_meta({"magic_limit": "ใช้ได้สามครั้ง", "magic_cost": "เสียเลือด"})
    assert result["magic_limit"] == "ไม่มี"
    assert result["magic_cost"] == "ไม่มี"
