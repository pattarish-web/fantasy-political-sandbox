"""
Fresh cast and fallback data generator for the strategic political-war fantasy reboot.
Maintains test compatibility while providing randomized attributes and names on every reset.
"""

import json
import random

# Faction concepts to build stances on
STANCE_BY_FACTION = {
    "สภาผู้สำเร็จราชการ": "เชื่อว่าความสงบต้องสร้างด้วยอำนาจที่มีขอบเขต และยอมเสียความนิยมเพื่อหยุดสงคราม",
    "กองทัพชายแดน": "ให้ความมั่นคงของผู้คนชายแดนมาก่อนคำสั่งจากเมืองหลวง ไม่ไว้ใจการเมืองที่ไม่เคยเห็นสนามรบ",
    "ศาสนจักรแห่งคำสัตย์": "เชื่อว่ากฎหมายและคำสัตย์ต้องอยู่เหนือผู้ปกครอง แม้ความจริงนั้นจะทำลายศาสนจักรของตน",
    "สมาพันธ์พ่อค้า": "เชื่อว่าการค้าและผลประโยชน์ร่วมกันลดสงครามได้ แต่พร้อมใช้หนี้และข้อมูลเป็นอาวุธ",
    "เครือข่ายใต้ดิน": "ต่อต้านรัฐที่ควบคุมประชาชน เชื่อว่าการลอบทำลายอำนาจคือราคาของอิสรภาพ",
    "ชุมชนลุ่มน้ำ": "เชื่อว่าชุมชนควรกำหนดอนาคตเอง ไม่ยอมให้ชนชั้นปกครองตัดสินแทนคนริมแม่น้ำ",
    "ราชสำนักเก่า": "เชื่อว่าราชสำนักเดิมควรได้อำนาจคืน แต่ต้องชำระความผิดในอดีตก่อนเรียกร้องความภักดี",
    "กองกำลังอิสระ": "เชื่อว่าคนธรรมดาไม่ควรถูกใช้เป็นเครื่องมือของสงคราม พร้อมหันดาบใส่ทุกฝ่ายที่ทำร้ายผู้บริสุทธิ์",
}

def stance_for_faction(faction, fallback="เชื่อว่าผลลัพธ์สำคัญกว่าวิธีการ"):
    return STANCE_BY_FACTION.get(str(faction).strip(), fallback)

# Pools for generating unique fallback character profiles dynamically if LLM is unavailable
GENDERS = ["ชาย", "หญิง"]
WEAPONS = ["ดาบสั้น", "คทาเวท", "พัดใบมีด", "มีดสั้น", "ดาบใหญ่", "หน้าไม้", "ไม้เท้าเหล็ก"]
SKIN_COLORS = ["ผิวสองสี", "ผิวแทน", "ผิวสีน้ำผึ้ง", "ผิวขาวซีด", "ผิวขาวอมชมพู"]

# Lists of international fantasy names translated into phonetic Thai
MALE_NAMES = ["ลูแคน", "ดัสเซอร์", "ทาเรน", "มาเรค", "กาเลน", "โรแกน", "ไซรัส", "เซนดริค"]
FEMALE_NAMES = ["วาเลเรีย", "ไลแซนดรา", "เคเลีย", "อาเรียนนา", "เซลีน", "เมรา", "อลิสซา", "ไอริส"]
SURNAMES = ["เวียร์", "เรน", "โซลเวน", "เมอร์โรว์", "น็อคต์", "เดรเวน", "เวล", "แอชฟอลล์", "ดอว์น", "เบลน"]

def _generate_fallback_meta(faction, gender, name):
    ambitions = [
        f"รวมอำนาจเพื่อปกป้องและพัฒนา{faction}",
        f"ทวงคืนชื่อเสียงและความยุติธรรมให้สหายใน{faction}",
        f"ทำให้ทุกฝ่ายยอมศิโรราบต่อระเบียบของ{faction}",
        f"ค้นหาความลับโบราณเพื่อความรุ่งเรืองของ{faction}"
    ]
    flaws = [
        "ระแวงคนง่ายจนไม่เหลือสหายแท้",
        "ยึดมั่นในอุดมการณ์เดิมจนปฏิเสธการประนีประนอม",
        "ใจร้อนตัดสินใจเร็วเกินไปยามตกอยู่ภายใต้แรงกดดัน",
        "ผูกใจเจ็บกับความล้มเหลวในอดีตจนมองข้ามความจำเป็นปัจจุบัน"
    ]
    weapons_pool = ["ดาบยาว", "คทาศักดิ์สิทธิ์", "ธนู", "กริชเงา", "ขวานศึก"]
    
    gender_tag = "1girl, female" if gender == "หญิง" else "1boy, male"
    title = f"ผู้พิทักษ์แห่ง{faction}"
    image_prompt = f"portrait of {gender_tag} character representing {faction}, fantasy clothing"
    
    sexualities = ["เฮเทอโรเซ็กชวล", "โฮโมเซ็กชวล", "ไบเซ็กชวล", "เอเซ็กชวล", "แพนเซ็กชวล"]
    return json.dumps({
        "gender": gender, "sexuality": random.choice(sexualities), "race": "มนุษย์",
        "age": f"{random.randint(22, 55)} ปี", "height": f"{random.randint(165, 185)} ซม.", "weight": f"{random.randint(50, 80)} กก.",
        "skin_color": random.choice(SKIN_COLORS), "skills": "การบริหารและการเจรจาต่อรอง",
        "weapon": random.choice(weapons_pool), "class_wealth": "ชนชั้นกลาง",
        "morality": stance_for_faction(faction), "ambition": random.choice(ambitions),
        "flaw": random.choice(flaws), "title": title, "image_prompt": image_prompt,
        "str": random.randint(55, 80), "int": random.randint(55, 80), "cha": random.randint(55, 80), "agi": random.randint(55, 80),
        "magic_school": "ไม่มีเวท", "element": "ไม่มีธาตุ",
        "magic_limit": "ไม่มี", "magic_cost": "ไม่มี",
        "discovery_status": "known",
    }, ensure_ascii=False)

def _build_initial_cast():
    """Generates 8 randomized fallback characters, one for each faction, with unique attributes."""
    factions = list(STANCE_BY_FACTION.keys())
    random.seed(random.randint(1, 999999))  # Ensure different seeds on every process load
    
    # Shuffle names to avoid duplication
    males = list(MALE_NAMES)
    females = list(FEMALE_NAMES)
    surnames = list(SURNAMES)
    random.shuffle(males)
    random.shuffle(females)
    random.shuffle(surnames)
    
    cast = []
    for i, faction in enumerate(factions):
        gender = random.choice(GENDERS)
        first_name = females.pop() if gender == "หญิง" else males.pop()
        last_name = surnames.pop()
        full_name = f"{first_name} {last_name}"
        
        personality = f"ผู้ศรัทธาใน{faction}ที่กล้าตัดสินใจ"
        power = f"การชักจูงคนด้วยอุดมการณ์ของ{faction}"
        meta = _generate_fallback_meta(faction, gender, full_name)
        
        cast.append((
            full_name,
            faction,
            personality,
            power,
            "Alive",
            meta
        ))
    return cast

# INITIAL_CHARACTERS must dynamically generate 8 items to satisfy core test suites immediately upon import
INITIAL_CHARACTERS = _build_initial_cast()
