"""Shared fantasy metadata rules used by spawn, simulation, and exports."""

from copy import deepcopy

DEFAULT_FANTASY_META = {
    "race": "มนุษย์",
    "magic_school": "ไม่มีเวท",
    "element": "ไม่มีธาตุ",
    "magic_limit": "ไม่มี",
    "magic_cost": "ไม่มี",
    "discovery_status": "known",
}

ALLOWED_RACES = {
    "มนุษย์", "เอลฟ์", "คนแคระ", "เงือก", "เผ่าเงา",
    "มนุษย์ดัดแปลง (ไซบอร์กแปรธาตุ)", "เอลฟ์ (ทรยศเผ่าพันธุ์)",
    "โฮมุนครุส (ครึ่งสัตว์ทดลอง)", "มนุษย์ (สายเลือดเทพ)",
    "มนุษย์ดัดแปลง", "โฮมุนครุส"
}
ALLOWED_ELEMENTS = {"ไม่มีธาตุ", "ไฟ", "น้ำ", "ลม", "ดิน", "เงา"}


def normalize_fantasy_meta(meta: dict | None) -> dict:
    """Fill missing fantasy fields and keep unknown values safe and readable."""
    result = deepcopy(DEFAULT_FANTASY_META)
    if isinstance(meta, dict):
        for key in result:
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                result[key] = value.strip()
    if result["race"] not in ALLOWED_RACES:
        print(f"[WorldRules] WARNING: Unknown race '{result['race']}' reset to default 'มนุษย์'")
        result["race"] = DEFAULT_FANTASY_META["race"]
    if result["element"] not in ALLOWED_ELEMENTS:
        print(f"[WorldRules] WARNING: Unknown element '{result['element']}' reset to default 'ไม่มีธาตุ'")
        result["element"] = DEFAULT_FANTASY_META["element"]
    if result["magic_school"] == "ไม่มีเวท":
        result["magic_limit"] = "ไม่มี"
        result["magic_cost"] = "ไม่มี"
    return result
