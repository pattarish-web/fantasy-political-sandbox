"""Canonical character data, legacy repair, and Thai display labels."""

import re
from copy import deepcopy


PROFILE_FIELDS = (
    "gender", "sexuality", "race", "age", "height", "weight", "skin_color",
    "skills", "weapon", "class_wealth", "morality", "ambition", "flaw", "title",
    "image_prompt",
)
STAT_FIELDS = ("str", "int", "cha", "agi")
FALLBACK = "ข้อมูลยังไม่ระบุ"

CHARACTER_NAME_ALIASES = {
    "นราอำพัน (Nara-Amphan)": "นราอำพัน",
    "นราอำพัน": "นราอำพัน",
}

_PROFILE_BACKFILL = {
    "จรัสรวี นิลธารา": {
        "sexuality": "ไบเซ็กชวล", "race": "มนุษย์", "age": "31 ปี", "height": "168 ซม.", "weight": "56 กก.",
        "skin_color": "ผิวน้ำผึ้ง", "skills": "การวิเคราะห์ผลึกเวท, การสืบสวนในห้องทดลอง", "weapon": "มีดผนึกผลึก",
        "class_wealth": "นักวิจัยหลวง (ฐานะปานกลาง)", "morality": "ความจริงต้องมาก่อนความภักดี", "ambition": "เปิดโปงผู้ควบคุมอาวุธต้นแบบ", "flaw": "ยึดติดกับหลักฐานจนมองข้ามความรู้สึกคน", "title": "ผู้เฝ้าผลึกต้องห้าม",
    },
    "ทวีป กฤษณะมิตร": {
        "race": "มนุษย์", "age": "38 ปี", "height": "172 ซม.", "weight": "62 กก.", "skin_color": "ผิวสีน้ำตาลอ่อน", "skills": "เวทผนึกคำสัตย์, การทูตระหว่างกิลด์", "weapon": "คทาผนึกเงา", "class_wealth": "ผู้นำกิลด์ (มั่งคั่ง)", "morality": "สมดุลสำคัญกว่าชัยชนะของฝ่ายใดฝ่ายหนึ่ง", "ambition": "สร้างเขตปลอดทหารให้ทุกฝ่ายเจรจา", "flaw": "เชื่อว่าพิธีกรรมแก้ความขัดแย้งได้เสมอ", "title": "ผู้พิทักษ์สภาเงา",
    },
    "ธนากร สยามกุล": {
        "race": "มนุษย์", "age": "34 ปี", "height": "178 ซม.", "weight": "72 กก.", "skin_color": "ผิวสองสี", "skills": "วาทศิลป์ราชสำนัก, อ่านเกมพันธมิตร", "weapon": "ดาบพิธีการ", "class_wealth": "ขุนนางชั้นกลาง", "morality": "ความสงบของราชสำนักต้องแลกด้วยการประนีประนอม", "ambition": "ยึดอำนาจสภาโดยไม่ก่อสงครามกลางเมือง", "flaw": "ประเมินความโกรธของประชาชนต่ำเกินไป", "title": "ทายาทผู้ประนีประนอม",
    },
    "นราอำพัน": {
        "race": "มนุษย์", "age": "32 ปี", "height": "165 ซม.", "weight": "54 กก.", "skin_color": "ผิวขาวเหลือง", "skills": "พิธีผูกคำสัตย์, การไกล่เกลี่ยทางการทูต", "weapon": "เข็มกลัดดอกบัวทอง", "class_wealth": "ผู้แทนสภา (ฐานะสูง)", "morality": "คำสัตย์มีค่ากว่าชีวิตของผู้กล่าว", "ambition": "ผูกพันธมิตรทั้งทวีปด้วยคำมั่นเดียว", "flaw": "ยอมเสียสละคนใกล้ตัวเพื่อเสถียรภาพ", "title": "ผู้ประสานสภาโลตัสทองคำ", "image_prompt": "ภาพพอร์ตเทรตหญิงผู้แทนสภา สวมชุดพิธีสีทองและถือดอกบัว",
    },
    "ปาริชาติ วีระกุล": {
        "race": "มนุษย์", "age": "29 ปี", "height": "167 ซม.", "weight": "53 กก.", "skin_color": "ผิวขาวอมทอง", "skills": "เจรจาลับ, สร้างกระแสข่าว, อ่านแรงจูงใจผู้คน", "weapon": "พัดใบมีดเงิน", "class_wealth": "ขุนนางราชสำนัก (มั่งคั่ง)", "morality": "ผลลัพธ์สำคัญกว่าวิธีการ", "ambition": "เปลี่ยนศาลหลวงให้เป็นอำนาจที่สาม", "flaw": "สะสมหนี้บุญคุณจนไม่มีใครรู้ใจจริง", "title": "ผู้เก็บบัญชีความแค้น",
    },
    "รัชต์ภูมิ สุริยะกุล": {
        "race": "มนุษย์", "age": "41 ปี", "height": "181 ซม.", "weight": "78 กก.", "skin_color": "ผิวแทน", "skills": "ปราศรัยปลุกใจ, ต่อรองผลประโยชน์, วางหมากการค้า", "weapon": "ดาบประจำตระกูล", "class_wealth": "ขุนนางพ่อค้า (มั่งคั่ง)", "morality": "ผู้ชนะเป็นผู้เขียนกฎหมาย", "ambition": "ครองเส้นทางการค้าทั้งทวีป", "flaw": "มั่นใจว่าทุกคนซื้อได้", "title": "เจ้าบ้านแห่งสุริยะกุล",
    },
    "วิศว์ วรพงษ์": {
        "race": "มนุษย์", "age": "36 ปี", "height": "176 ซม.", "weight": "70 กก.", "skin_color": "ผิวสีน้ำผึ้ง", "skills": "การทูต, ปลุกระดมชนชั้นกลาง, วางเครือข่ายสายข่าว", "weapon": "ไม้เท้าซ่อนดาบ", "class_wealth": "ขุนนางใหม่ (มั่งคั่ง)", "morality": "อำนาจต้องมีภาพลักษณ์ที่ชอบธรรม", "ambition": "สร้างอาณาจักรที่ตนเป็นผู้ไกล่เกลี่ยทุกฝ่าย", "flaw": "กลัวการถูกลืมมากกว่าการถูกเกลียด", "title": "นักการทูตแห่งดวงอาทิตย์ทอง",
    },
    "อัชฌา จันทร์ประทีป": {
        "race": "มนุษย์", "age": "27 ปี", "height": "163 ซม.", "weight": "51 กก.", "skin_color": "ผิวขาวอมชมพู", "sexuality": "เฮเทอโรเซ็กชวล", "skills": "ผูกเสียงสะท้อนคำสัตย์, การเมืองในวงสังคม", "weapon": "พู่กันผนึกความทรงจำ", "class_wealth": "ผู้อุปถัมภ์ศิลปิน (มั่งคั่ง)", "morality": "ความทรงจำของผู้คนคือสนามรบที่แท้จริง", "ambition": "ทำให้คำสัญญาของตนกลายเป็นกฎหมายที่ทุกคนเชื่อ", "flaw": "ไม่ยอมปล่อยวางความแค้นเก่า", "title": "ผู้ร้อยเสียงจันทร์", "image_prompt": "ภาพพอร์ตเทรตหญิงนักอุปถัมภ์ สวมชุดสีครามใต้แสงจันทร์",
    },
}

_SKIN_BACKFILL = {
    "จักรพรรดิไรเซน": "ผิวขาวซีด", "แม่ทัพหญิงวาเลเรีย": "ผิวขาวซีด", "เอลลิส ปราชญ์แปรธาตุ": "ผิวขาวอมชมพู", "พ่อค้าอาวุธซาเคียน": "ผิวขาวอมทอง", "ลูคัส ผู้นำกบฏ": "ผิวแทนแดด", "เนีย นักฆ่าเงา": "ผิวซีดอมเทา", "อาร์คบิชอปโซลาร์": "ผิวขาวซีด", "อัศวินเทมพลาร์ ไซริส": "ผิวขาวอมชมพู",
}

_CORE_TRANSLATIONS = {
    "นราอำพัน": ("สภาโลตัสทองคำ", "ผู้ไกล่เกลี่ยใจเย็นและอดทน อ่านเกมการเมืองได้เฉียบคม รักษาความอบอุ่นภายนอกแต่มีเครือข่ายข่าวกรองส่วนตัว", "[ผูกเสียงกระซิบ] ผูกคำสัญญาที่กล่าวในพิธีเข้ากับชะตา ทำให้ผู้ให้คำสัตย์ฝืนคำพูดได้ยาก"),
    "ปาริชาติ วีระกุล": ("ศาลาแห่งผ้าคลุมสีฝักทอง", "ขุนนางวาจาคม สุขุมและคำนวณผลประโยชน์ ชอบข้อตกลงลับมากกว่าคำปราศรัย", "[ใยอิทธิพล] มองเห็นและเร่งกระแสความเชื่อที่ไหลอยู่ใต้สังคมให้กลายเป็นความเห็นส่วนรวม"),
    "รัชต์ภูมิ สุริยะกุล": ("บ้านสุริยะกุล", "มีเสน่ห์และเจ้าเล่ห์ เชี่ยวชาญการชักจูงและซ่อนวาระของตน", "[วาทะสะกดใจ] โน้มน้าวแม้แต่ผู้ที่ไม่ไว้วางใจได้ด้วยการเลือกถ้อยคำอย่างแม่นยำ"),
    "วิศว์ วรพงษ์": ("บ้านสุริยะทอง", "ทะเยอทะยานและมีเสน่ห์ เชี่ยวชาญการชักใยผู้คนผ่านการทูต", "[วาทะนักการทูต] ทำให้คู่เจรจาเปิดใจและยอมรับทางออกที่ตนเสนอ"),
    "อัชฌา จันทร์ประทีป": ("สภาคลองจันทร์", "สุภาพและทะเยอทะยานอย่างเงียบงัน สะสมคำชมและความลับราวกับบัญชีหนี้", "[เสียงสะท้อนคำสัตย์] ทำให้คำสัญญาที่ได้ยินติดอยู่ในความทรงจำและมีน้ำหนักน่าเชื่อถือขึ้น"),
}

_TERM_MAP = {
    "female": "หญิง", "male": "ชาย", "non-binary": "นอนไบนารี", "heterosexual": "เฮเทอโรเซ็กชวล", "homosexual": "โฮโมเซ็กชวล", "pansexual": "แพนเซ็กชวล", "bisexual": "ไบเซ็กชวล", "asexual": "เอเซ็กชวล", "celibate": "พรหมจรรย์",
}

RELATIONSHIP_TYPE_LABELS = {"split_loyalty": "ความภักดีแตกเป็นสองฝ่าย", "schism": "ความแตกแยก", "sever": "ตัดขาด", "trust_undermined": "ความไว้วางใจถูกสั่นคลอน", "trust_broken": "ความไว้วางใจพังทลาย", "debt/bargain": "หนี้บุญคุณและข้อตกลง"}
STATUS_LABELS = {"Alive": "มีชีวิต", "Dead": "เสียชีวิต"}


def canonicalize_character_name(name: str) -> str:
    value = str(name or "").strip()
    return CHARACTER_NAME_ALIASES.get(value, value)


def normalize_display_value(field: str, value):
    if value is None or value == "":
        return FALLBACK
    if field == "image_prompt" or field == "image_prompts":
        return value
    if field in {"height", "weight"}:
        text = str(value).strip()
        text = re.sub(r"\s*(?:cm|ซม\.?|เซนติเมตร)\s*$", " ซม.", text, flags=re.I)
        text = re.sub(r"\s*(?:kg|กก\.?|กิโลกรัม)\s*$", " กก.", text, flags=re.I)
        return text
    text = str(value).strip()
    lowered = text.lower()
    for term, label in _TERM_MAP.items():
        if term in lowered:
            return label
    return text


def normalize_meta(meta: dict | None, name: str) -> dict:
    source = deepcopy(meta) if isinstance(meta, dict) else {}
    canonical_name = canonicalize_character_name(name)
    backfill = {**_PROFILE_BACKFILL.get(canonical_name, {}), **({"skin_color": _SKIN_BACKFILL[canonical_name]} if canonical_name in _SKIN_BACKFILL else {})}
    normalized = {}
    for field in PROFILE_FIELDS:
        if field == "image_prompt" and field not in source and field not in backfill:
            continue
        value = normalize_display_value(field, source.get(field))
        if value == FALLBACK:
            value = backfill.get(field, FALLBACK)
        normalized[field] = value
    for field in STAT_FIELDS:
        value = source.get(field, 50)
        try:
            value = max(1, min(100, int(value)))
        except (TypeError, ValueError):
            value = 50
        normalized[field] = value
    for key in ("image_prompts", "relationship_target", "relationship_type"):
        if key in source:
            normalized[key] = source[key]
    return normalized


def normalize_character_core(name: str, faction: str, personality: str, special_power: str) -> tuple[str, str, str, str]:
    canonical_name = canonicalize_character_name(name)
    translated = _CORE_TRANSLATIONS.get(canonical_name)
    if translated:
        return canonical_name, *translated
    return canonical_name, normalize_display_value("faction", faction), normalize_display_value("personality", personality), normalize_display_value("special_power", special_power)


def relationship_type_label(value: str) -> str:
    return RELATIONSHIP_TYPE_LABELS.get(str(value or ""), str(value or FALLBACK))


def status_label(value: str) -> str:
    raw = str(value or "").strip()
    return STATUS_LABELS.get(raw, STATUS_LABELS.get(raw.title(), raw or FALLBACK))
