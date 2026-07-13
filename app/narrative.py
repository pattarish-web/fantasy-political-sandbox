"""Stable narrative reference data shared by simulation and Historian."""

from copy import deepcopy


WORLD_BIBLE = {
    "version": 1,
    "setting": (
        "อาณาจักรนี้เป็นแฟนตาซีเวทกล: เวทมนตร์ แปรธาตุ และเครื่องกลอยู่ร่วมกัน "
        "ผลึกบันทึกภาพและเครือข่ายเวทกลส่งข่าวได้ แต่ไม่ใช่เทคโนโลยีร่วมสมัย"
    ),
    "register": "บรรยายภาษาไทยร่วมสมัยแบบวรรณศิลป์; ตัวละครใช้สรรพนามตามฐานะอย่างคงเส้นคงวา",
    "factions": {
        "จักรวรรดิเหล็กกล้า": {
            "objective": "รักษาความเป็นเอกภาพด้วยกองทัพและอำนาจกลาง",
            "leverage": "ปราการ กองทัพ และระบบราชการ",
            "pressure": "ความชอบธรรมของผู้ปกครองและความภักดีของกองทัพ",
        },
        "กบฏผู้ปลดแอก": {
            "objective": "ปลดปล่อยผู้ถูกกดขี่และตั้งระเบียบการเมืองใหม่",
            "leverage": "แรงสนับสนุนจากชุมชนและเครือข่ายใต้ดิน",
            "pressure": "การสูญเสียผู้นำและการตอบโต้ต่อพลเรือน",
        },
        "ภาคีจอมเวทศักดิ์สิทธิ์": {
            "objective": "คุ้มครองอำนาจศาสนาและความบริสุทธิ์ของเวทมนตร์",
            "leverage": "ศรัทธาสาธารณะและนักรบศักดิ์สิทธิ์",
            "pressure": "ความแตกแยกภายในและการต่อต้านเวทกล",
        },
        "สมาพันธ์นักเล่นแร่แปรธาตุ": {
            "objective": "ควบคุมความรู้ สิทธิบัตร และเศรษฐกิจเวทกล",
            "leverage": "ห้องทดลอง อาวุธ และหนี้ทางการค้า",
            "pressure": "ผลลัพธ์ของงานทดลองและความไม่ไว้วางใจจากทุกฝ่าย",
        },
    },
}

# Reboot direction: intimate losses and betrayals must grow out of the political
# conflict instead of appearing as disconnected subplots.
REBOOT_GUIDELINES = (
    "แนวทางโลกใหม่: แฟนตาซีสงครามการเมืองเชิงกลยุทธ์; ทุกชัยชนะต้องแลกด้วย "
    "มิตรภาพ ความรัก หรือชีวิต. หนึ่งตอนมีเหตุการณ์หลักเดียว เปิดปมทีละชั้น "
    "และแสดงผลกระทบต่อคนธรรมดาก่อนขยับไปสู่ฉากใหญ่."
)

FANTASY_RULES = (
    "กฎแฟนตาซี: เวททุกชนิดต้องมีจุดอ่อนและราคาที่ต้องจ่าย; ตัวละครหนึ่งคนมีเวทหลักและธาตุเด่นได้อย่างละหนึ่งอย่าง "
    "เผ่าใหม่ต้องมีเบาะแสหรือเหตุการณ์ปูพื้นก่อนเปิดเผย และผลของเวท/เผ่าต้องทิ้งร่องรอยต่อเนื่องในตอนถัดไป"
)


def format_world_bible() -> str:
    """Return the compact setting reference used in LLM prompts."""
    faction_lines = []
    for name, details in WORLD_BIBLE["factions"].items():
        faction_lines.append(
            f"- {name}: เป้าหมาย={details['objective']} | "
            f"อำนาจต่อรอง={details['leverage']} | แรงกดดัน={details['pressure']}"
        )
    return "\n".join(
        [
            f"โลก: {WORLD_BIBLE['setting']}",
            f"น้ำเสียง: {WORLD_BIBLE['register']}",
            REBOOT_GUIDELINES,
            FANTASY_RULES,
            "การเมืองแต่ละฝ่าย:",
            *faction_lines,
        ]
    )


def build_faction_ledger(characters: list[dict], wars: list[dict]) -> dict:
    """Merge stable faction motives with the world tables' current pressure."""
    if wars is None:
        wars = []
    ledger = deepcopy(WORLD_BIBLE["factions"])
    for character in characters:
        faction = character.get("faction")
        if not faction:
            continue
        details = ledger.setdefault(
            faction,
            {"objective": "ยังไม่ทราบ", "leverage": "ยังไม่ทราบ", "pressure": "กำลังประเมิน"},
        )
        status = character.get("status", "Alive")
        details.setdefault("members", []).append(
            {"name": character.get("name", ""), "status": status}
        )
    for war in wars:
        for faction in (war.get("aggressor_faction"), war.get("defender_faction")):
            if faction:
                ledger.setdefault(
                    faction,
                    {"objective": "ยังไม่ทราบ", "leverage": "ยังไม่ทราบ", "pressure": "สงคราม"},
                )
                ledger[faction]["pressure"] = "สงคราม"
    return ledger
