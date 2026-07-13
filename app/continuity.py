"""Deterministic checks that keep generated events consistent with the world state."""

from datetime import datetime


def validate_event_continuity(event: dict, *, known_races: set[str], current_time: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(event, dict):
        return ["เหตุการณ์ต้องเป็นข้อมูลแบบวัตถุ"]
    timestamp = event.get("timestamp")
    if current_time and timestamp:
        try:
            if datetime.fromisoformat(str(timestamp)) < datetime.fromisoformat(str(current_time)):
                errors.append("ลำดับเวลาในเหตุการณ์ย้อนกลับ")
        except ValueError:
            errors.append("รูปแบบเวลาไม่ถูกต้อง")
    race = event.get("new_race")
    if race and race not in known_races and not event.get("foreshadowing"):
        errors.append("เผ่าใหม่ยังไม่มีเบาะแสหรือเหตุการณ์ปูพื้น")
    unknown = set(event.get("requires_knowledge", []) or []) - set(event.get("known_facts", []) or [])
    if unknown:
        errors.append("ตัวละครอ้างข้อมูลที่ยังไม่รู้")
    return errors
