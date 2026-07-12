import json
from pathlib import Path

chars = [
    {
        'name': 'จักรพรรดิไรเซน',
        'faction': 'จักรวรรดิเหล็กกล้า',
        'personality': 'เผด็จการผู้เยือกเย็น ทะเยอทะยาน ต้องการรวบรวมทวีปให้เป็นหนึ่งเดียวด้วยกำลังทหาร',
        'special_power': '[อำนาจแห่งราชันย์] แผ่จิตสังหารกดดันศัตรูให้ขยับไม่ได้และสร้างเกราะพลังจิตที่ป้องกันการโจมตีทุกชนิด',
        'status': 'Alive',
        'meta': {
            'str': 80, 'int': 90, 'cha': 95, 'agi': 50,
            'race': 'มนุษย์', 'age': 45, 'height': '188cm', 'weight': '85kg',
            'gender': 'ชาย', 'sexuality': 'Heterosexual',
            'skills': 'การปกครองระดับเผด็จการ, ยุทธวิธีการรบระดับปรมาจารย์',
            'weapon': 'ดาบเพลิงโลกันตร์',
            'title': 'ผู้พิชิตแห่งเหล็กกล้า',
            'ambition': 'รวมแผ่นดินเป็นหนึ่งเดียวโดยใช้สงครามและการแปรธาตุเป็นเครื่องมือ',
            'flaw': 'หวาดระแวงการถูกทรยศอย่างหนัก',
            'class_wealth': 'จักรพรรดิ (มั่งคั่งมหาศาล)',
            'morality': 'อำนาจคือความถูกต้อง การนองเลือดเป็นเพียงเส้นทางสู่ความสงบ',
            'image_prompt': '1boy, adult, handsome male emperor, cold gaze, anime style, wearing black and gold military uniform with a long cape, fiery sword at his side, dark hair, dramatic lighting, masterpiece, highly detailed'
        }
    },
    {
        'name': 'แม่ทัพหญิงวาเลเรีย',
        'faction': 'จักรวรรดิเหล็กกล้า',
        'personality': 'เข้มงวด จงรักภักดี และโหดเหี้ยมในสนามรบ เชื่อว่าความแข็งแกร่งคือทุกสิ่ง',
        'special_power': '[กายาเหล็กไหล] เปลี่ยนผิวหนังตนเองให้แข็งแกร่งดุจเพชรและป้องกันเวทมนตร์ได้ 80%',
        'status': 'Alive',
        'meta': {
            'str': 95, 'int': 65, 'cha': 80, 'agi': 70,
            'race': 'มนุษย์ดัดแปลง (ไซบอร์กแปรธาตุ)', 'age': 28, 'height': '175cm', 'weight': '65kg',
            'gender': 'หญิง', 'sexuality': 'Asexual',
            'skills': 'การต่อสู้ระยะประชิดระดับปรมาจารย์, คุมกองทัพแนวหน้า',
            'weapon': 'หอกกลไกเจาะเกราะ',
            'title': 'คมเขี้ยวแห่งจักรวรรดิ',
            'ambition': 'กำจัดศัตรูของจักรพรรดิให้สิ้นซาก',
            'flaw': 'ขาดความเห็นอกเห็นใจ และซื่อสัตย์จนตาย',
            'class_wealth': 'ขุนนางทหารชั้นสูง (ร่ำรวย)',
            'morality': 'หน้าที่เหนือสิ่งอื่นใด',
            'image_prompt': '1girl, mature female anime character, silver hair, sharp red eyes, wearing silver and crimson futuristic armor, holding a mechanical spear, battle-hardened, anime style, masterpiece, dynamic pose, 4k'
        }
    },
    {
        'name': 'เอลลิส ปราชญ์แปรธาตุ',
        'faction': 'สมาพันธ์นักเล่นแร่แปรธาตุ',
        'personality': 'อัจฉริยะผู้หมกมุ่นกับการวิจัย โลกส่วนตัวสูง มองทุกอย่างเป็นสมการและวัตถุดิบ',
        'special_power': '[แปรธาตุพริบตา] เปลี่ยนโครงสร้างสสารรอบตัวได้ทันทีโดยไม่ต้องวาดวงเวท (เช่น เปลี่ยนเหล็กเป็นทราย เปลี่ยนน้ำเป็นระเบิด)',
        'status': 'Alive',
        'meta': {
            'str': 20, 'int': 100, 'cha': 60, 'agi': 40,
            'race': 'มนุษย์', 'age': 24, 'height': '160cm', 'weight': '48kg',
            'gender': 'หญิง', 'sexuality': 'Bisexual',
            'skills': 'วิทยาการแปรธาตุระดับตำนาน, ประดิษฐ์อาวุธชีวภาพ',
            'weapon': 'ถุงมือแปรธาตุสั่งการ',
            'title': 'สติเฟื่องแห่งยุค',
            'ambition': 'ค้นพบสมการผู้สร้างที่จะไขความลับของชีวิตและความตาย',
            'flaw': 'ขาดความสามารถในการเข้าสังคม และมองคนเป็นแค่หนูทดลอง',
            'class_wealth': 'ผู้อำนวยการสมาพันธ์ (ร่ำรวยจากสิทธิบัตร)',
            'morality': 'ความรู้สำคัญกว่าศีลธรรม',
            'image_prompt': '1girl, anime style, messy blonde hair, round glasses, wearing a white alchemist coat over a steampunk corset, glowing alchemy circles in background, holding a glowing potion, masterpiece, highly detailed, cute but crazy expression'
        }
    },
    {
        'name': 'พ่อค้าอาวุธซาเคียน',
        'faction': 'สมาพันธ์นักเล่นแร่แปรธาตุ',
        'personality': 'หน้าไหว้หลังหลอก ลื่นไหลเหมือนปลาไหล สนใจแต่ผลกำไรจากการขายอาวุธให้ทุกฝ่ายรบกัน',
        'special_power': '[เนตรประเมิน] มองทะลุจุดอ่อนของทั้งสิ่งของและสิ่งมีชีวิตได้ในพริบตา',
        'status': 'Alive',
        'meta': {
            'str': 30, 'int': 85, 'cha': 95, 'agi': 60,
            'race': 'เอลฟ์ (ทรยศเผ่าพันธุ์)', 'age': 150, 'height': '182cm', 'weight': '70kg',
            'gender': 'ชาย', 'sexuality': 'Pansexual',
            'skills': 'การเจรจาการค้าระดับปรมาจารย์, ปั่นป่วนการเมือง',
            'weapon': 'แหวนซ่อนเข็มพิษ',
            'title': 'จ้าวแห่งตลาดมืด',
            'ambition': 'เป็นผู้กุมเศรษฐกิจและการเมืองทั้งหมดผ่านหนี้สินและอาวุธ',
            'flaw': 'ความโลภไม่สิ้นสุด และไม่มีใครไว้ใจอย่างแท้จริง',
            'class_wealth': 'พ่อค้าตลาดมืด (มหาเศรษฐี)',
            'morality': 'เงินซื้อได้ทุกอย่าง รวมถึงชีวิตคน',
            'image_prompt': '1boy, male elf, anime style, long silver hair tied in a ponytail, sly smirk, wearing elegant merchant clothes with gold steampunk accents, tossing a gold coin, dark alleys background, masterpiece, 8k resolution'
        }
    },
    {
        'name': 'ลูคัส ผู้นำกบฏ',
        'faction': 'กบฏผู้ปลดแอก',
        'personality': 'อดีตทาสผู้ลุกฮือ รักความยุติธรรม กล้าหาญ และพร้อมตายเพื่อปลดปล่อยผู้กดขี่',
        'special_power': '[เพลิงปฏิวัติ] ควบคุมเปลวไฟสีน้ำเงินที่ไม่มีวันดับจนกว่าเป้าหมายจะมอดไหม้ ยิ่งจิตใจมุ่งมั่นไฟยิ่งแรง',
        'status': 'Alive',
        'meta': {
            'str': 85, 'int': 70, 'cha': 90, 'agi': 75,
            'race': 'มนุษย์', 'age': 25, 'height': '180cm', 'weight': '75kg',
            'gender': 'ชาย', 'sexuality': 'Heterosexual',
            'skills': 'ศิลปะการต่อสู้ข้างถนน, วาทศิลป์ปลุกใจฝูงชน',
            'weapon': 'ดาบใหญ่บิ่นๆ ที่ขโมยมาจากทหาร',
            'title': 'ประกายไฟแห่งความหวัง',
            'ambition': 'ทำลายจักรวรรดิเหล็กกล้าและสถาปนาสาธารณรัฐ',
            'flaw': 'ใจร้อนและยอมเสี่ยงชีวิตตัวเองเพื่อปกป้องคนอื่นมากเกินไป',
            'class_wealth': 'ผู้ยากไร้ (ไม่มีสมบัติมีแต่อุดมการณ์)',
            'morality': 'ความยุติธรรมต้องแลกมาด้วยเลือด',
            'image_prompt': '1boy, young male, anime style, fiery blue aura, rugged appearance, scarred face, wearing torn rebel clothes with a red scarf, holding a giant broken sword, determined eyes, masterpiece, intense battlefield background'
        }
    },
    {
        'name': 'เนีย นักฆ่าเงา',
        'faction': 'กบฏผู้ปลดแอก',
        'personality': 'เงียบขรึม พูดน้อยต่อยหนัก อดีตหนูทดลองของสมาพันธ์แปรธาตุที่หนีออกมาได้',
        'special_power': '[รอยแยกมิติ] สามารถเทเลพอร์ตตัวเองในระยะสั้นๆ ผ่านเงาของสิ่งต่างๆ ได้',
        'status': 'Alive',
        'meta': {
            'str': 50, 'int': 75, 'cha': 40, 'agi': 100,
            'race': 'โฮมุนครุส (ครึ่งสัตว์ทดลอง)', 'age': 18, 'height': '155cm', 'weight': '45kg',
            'gender': 'หญิง', 'sexuality': 'Asexual',
            'skills': 'ลอบสังหารระดับปรมาจารย์, หลบซ่อนตัวในเงามืด',
            'weapon': 'มีดสั้นอาบยาพิษสลายเซลล์',
            'title': 'มัจจุราชไร้เสียง',
            'ambition': 'ล้างแค้นสมาพันธ์นักเล่นแร่แปรธาตุที่จับเธอไปทดลอง',
            'flaw': 'หวาดกลัวแสงสว่างจัดๆ และไว้ใจใครยากมาก',
            'class_wealth': 'ทหารรับจ้าง/นักฆ่า (พอมีพอกิน)',
            'morality': 'ฆ่าคนที่สมควรตายเท่านั้น',
            'image_prompt': '1girl, anime style, short black hair, purple glowing eyes, wearing tight black assassin stealth suit with a hood, holding dual poison daggers, shadow teleportation effect, dark and mysterious, masterpiece'
        }
    },
    {
        'name': 'อาร์คบิชอปโซลาร์',
        'faction': 'ภาคีจอมเวทศักดิ์สิทธิ์',
        'personality': 'นักบวชสูงสุดผู้ยึดมั่นในเวทมนตร์บริสุทธิ์ เกลียดชังการแปรธาตุและเทคโนโลยี มองว่าเป็นสิ่งนอกรีต',
        'special_power': '[แสงแห่งพระเจ้า] ร่ายเวทมนตร์แสงทำลายล้างเป็นวงกว้าง สามารถชำระล้างเวทมนตร์และคำสาปได้ทุกชนิด',
        'status': 'Alive',
        'meta': {
            'str': 30, 'int': 95, 'cha': 85, 'agi': 40,
            'race': 'มนุษย์ (สายเลือดเทพ)', 'age': 60, 'height': '178cm', 'weight': '70kg',
            'gender': 'ชาย', 'sexuality': 'Heterosexual',
            'skills': 'เวทมนตร์ศักดิ์สิทธิ์ระดับปาฏิหาริย์, การเมืองศาสนา',
            'weapon': 'คทาพฤกษาแสง',
            'title': 'ผู้ชำระล้างความบาป',
            'ambition': 'ทำลายเทคโนโลยีแปรธาตุทั้งหมดเพื่อนำพาโลกกลับสู่ยุคแห่งเวทมนตร์',
            'flaw': 'อนุรักษ์นิยมสุดโต่ง และมองผู้ใช้เทคโนโลยีเป็นศัตรูทั้งหมด',
            'class_wealth': 'ผู้นำสูงสุดทางศาสนา (มั่งคั่ง)',
            'morality': 'ความบริสุทธิ์ของเวทมนตร์คือสัจธรรม ฆ่าคนบาปไม่ผิด',
            'image_prompt': '1boy, older male anime character, long white beard and hair, wearing majestic white and gold holy robes, holding a glowing divine staff, glowing halo aura, stained glass church background, masterpiece, divine lighting'
        }
    },
    {
        'name': 'อัศวินเทมพลาร์ ไซริส',
        'faction': 'ภาคีจอมเวทศักดิ์สิทธิ์',
        'personality': 'อัศวินศักดิ์สิทธิ์ที่เต็มไปด้วยข้อสงสัยในคำสอนของภาคี แอบศึกษาความรู้การแปรธาตุอย่างลับๆ',
        'special_power': '[ผนึกต้านทาน] สร้างโดมพลังงานที่สะท้อนการโจมตีเวทมนตร์และการระเบิดได้ 100%',
        'status': 'Alive',
        'meta': {
            'str': 85, 'int': 80, 'cha': 75, 'agi': 60,
            'race': 'มนุษย์', 'age': 26, 'height': '185cm', 'weight': '80kg',
            'gender': 'ชาย', 'sexuality': 'Homosexual',
            'skills': 'วิชาดาบศักดิ์สิทธิ์ระดับสูง, การแปรธาตุเบื้องต้น (ลับ)',
            'weapon': 'ดาบและโล่สลักรูน',
            'title': 'อัศวินผู้กังขา',
            'ambition': 'ผสานพลังเวทมนตร์และการแปรธาตุเข้าด้วยกันเพื่อยุติสงครามระหว่างสองฝั่ง',
            'flaw': 'มีความลับทรยศภาคี ทำให้ต้องระแวงตลอดเวลา',
            'class_wealth': 'ทหารศาสนจักร (ฐานะปานกลาง)',
            'morality': 'หาความจริงที่ซ่อนอยู่เบื้องหลังความขัดแย้ง',
            'image_prompt': '1boy, handsome male anime character, short blond hair, wearing silver holy knight armor with a blue cape, holding a rune-engraved sword and shield, looking conflicted, masterpiece, cinematic anime style'
        }
    }
]

code = 'INITIAL_CHARACTERS = [\n'
for char in chars:
    m = json.dumps(char['meta'], ensure_ascii=False)
    # The tuple is: (name, faction, personality, power, status, meta_data)
    t = (char['name'], char['faction'], char['personality'], char['special_power'], char['status'], m)
    code += f'    {repr(t)},\n'
code += ']\n\n'
code += 'LOCATIONS = [\n'
code += '    "เขตปลอดทหาร (No Man\'s Land)", "ปราการเหล็กกล้า (Iron Fortress)", "สถาบันวิจัยแปรธาตุ (Alchemy Hub)",\n'
code += '    "มหาวิหารศักดิ์สิทธิ์", "สลัมใต้เมือง", "ตลาดมืดค้าอาวุธเถื่อน",\n'
code += '    "ป่าต้องห้าม (Forbidden Forest)", "ลานประหารกลางแจ้ง"\n'
code += ']\n'

output_path = Path(__file__).parent / 'app' / 'seed_data.py'
output_path.write_text(code, encoding='utf-8')
print(f'Seed data generated successfully at {output_path}')
