# Character Integrity and Thai Localization Design

## Goal

ทำให้โปรไฟล์ตัวละครทุกตัวมีข้อมูลที่ใช้งานได้ แสดงผลภาษาไทยอย่างสม่ำเสมอ และทำให้ log/บท/ความสัมพันธ์อ้างถึงตัวละครเดียวกันด้วยชื่อ canonical เดียว

## Current evidence

- ตัวละครในฐานข้อมูล 16 ตัวมีช่อง `skin_color` ว่างทั้งหมด และ 8 ตัวขาดข้อมูลโปรไฟล์เชิงลึกหลายช่อง
- `CharacterSpawnResult` ทำให้ข้อมูลโปรไฟล์ส่วนใหญ่เป็น optional จึงยอมรับตัวละครที่สร้างไม่ครบ
- `export_html.py` แสดงค่า status และ relationship type ดิบ และ `_render_meta` แสดง `-` เมื่อว่าง
- ข้อมูลเก่ามีชื่อ `นราอำพัน` แต่ roster ใช้ `นราอำพัน (Nara-Amphan)` ทำให้ log 3 รายการและความสัมพันธ์ 1 รายการเชื่อมไม่ถึงโปรไฟล์

## Chosen approach

ใช้ชั้นข้อมูลกลางขนาดเล็กใน `app/character_data.py` แล้วให้ฐานข้อมูลเรียก normalization ตอน `init_db()` และตอนเพิ่มตัวละคร:

1. กำหนดข้อมูลขั้นต่ำและค่า backfill ที่เป็นภาษาไทยสำหรับตัวละครเก่าที่ระบุได้ พร้อมค่า fallback ภาษาไทยสำหรับตัวละครใหม่ที่สร้างผ่าน API ระดับต่ำ
2. แปลค่ามาตรฐานที่หลุดมา (`female`, `Male`, `Heterosexual`, `cm`, `kg`) ก่อนเก็บ/ก่อน export โดยไม่แตะ prompt ภาพที่ต้องเป็นภาษาอังกฤษสำหรับ image model
3. canonicalize ชื่อ alias ก่อนเขียน logs, chapters และ relationships; ตรวจ foreign references ระหว่าง migration และแก้ alias เดิมแบบ idempotent
4. ให้ schema และ parser ของตัวละครใหม่บังคับ field เรื่องราวหลักและค่าสถานะทั้งหมดที่หน้าโปรไฟล์ใช้
5. ให้หน้า export แปล status/relationship type และใช้ข้อความ fallback ภาษาไทยแทนเครื่องหมายขีด

ทางเลือกที่ไม่เลือกคือ (ก) แก้เฉพาะ HTML ซึ่งจะทิ้งข้อมูลเสียใน DB และ (ข) ลบตัวละครที่ข้อมูลไม่ครบ ซึ่งทำลายความต่อเนื่องของเรื่อง

## Data flow and safety

`LLM JSON -> CharacterSpawnResult -> parser validation -> normalize profile -> insert_character -> init_db migration -> HTML export`.

Normalization เติมเฉพาะค่าที่ว่าง ไม่เขียนทับข้อมูลเนื้อเรื่องที่มีอยู่แล้ว ยกเว้น alias และค่ามาตรฐานภาษาอังกฤษที่มี mapping แน่นอน การ migration ทำซ้ำได้และไม่สร้างความสัมพันธ์ซ้ำ

## Testing and deployment acceptance

- มี regression tests สำหรับ profile completeness, English display normalization และ broken-name repair
- ชุดทดสอบเดิมต้องผ่านทั้งหมด
- inventory หลัง migration ต้องไม่มี missing profile fields หรือ reference ที่ชี้ไปยังชื่อที่ไม่มีใน roster
- สร้าง static chronicle ใหม่, commit, push `master`, และตรวจ GitHub Pages deployment สำเร็จ
