# Fantasy Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** เพิ่มระบบแฟนตาซีและ continuity gate ให้การสร้างตัวละคร/จำลอง/เขียนตอนสอดคล้องกันโดยไม่ทำให้ workflow ล้มเหลวเมื่อข้อมูล AI ไม่ครบ

**Architecture:** ใช้ World Bible และ registry เป็นข้อมูลกลาง, เก็บ metadata ใหม่ใน `characters.meta_data` และตรวจผลลัพธ์ผ่าน normalization/continuity layer ก่อนบันทึก การแสดงผลอ่าน metadata เดียวกันเพื่อป้องกันข้อมูลซ้ำหลายแหล่ง

**Tech Stack:** Python, Pydantic, SQLite metadata JSON, pytest, HTML export

## Global Constraints

- ชื่อและข้อมูลที่ผู้ใช้อ่านต้องเป็นภาษาไทยหรือคำอ่านไทยเท่านั้น
- เวทหลักและธาตุเด่นของตัวละครมีได้อย่างละหนึ่งรายการเป็นค่าเริ่มต้น
- ทุกเวทต้องมีจุดอ่อนและต้นทุน
- เผ่าใหม่ต้องมีเบาะแส/เหตุการณ์ก่อนเปลี่ยนเป็น discovered
- ข้อมูล AI ไม่ครบต้อง fallback แทนการล้มเหลวโดยไม่จำเป็น

### Task 1: Add fantasy world data and normalization

**Files:**
- Modify: `app/narrative.py`
- Modify: `app/seed_data_new.py`
- Create: `app/world_rules.py`
- Test: `tests/test_world_rules.py`

- [ ] เขียน tests สำหรับค่าเริ่มต้น การจำกัดเวท และ registry เผ่าที่ซ่อนอยู่
- [ ] เพิ่ม constants สำหรับเผ่า ธาตุ สำนักเวท จุดอ่อน ต้นทุน และฟังก์ชัน `normalize_fantasy_meta(meta)`
- [ ] ผนวกกฎเข้าสู่ `format_world_bible()` และ metadata ตัวละครเริ่มต้น
- [ ] รัน `pytest tests/test_world_rules.py -q`
- [ ] Commit: `feat: add fantasy world rules and normalization`

### Task 2: Extend character schema and spawn fallback

**Files:**
- Modify: `app/schemas.py`
- Modify: `app/spawn.py`
- Test: `tests/test_spawn_fantasy_fields.py`

- [ ] เขียน tests กรณีฟิลด์หายและกรณีค่าผิดกฎ
- [ ] เพิ่มฟิลด์เผ่า ธาตุ สำนักเวท จุดอ่อน ต้นทุน แบบมีค่า fallback
- [ ] ทำให้ spawn normalize และ reject เฉพาะข้อมูลที่แก้ไม่ได้
- [ ] รัน focused spawn tests และชุด tests เดิม
- [ ] Commit: `feat: validate fantasy character fields`

### Task 3: Add timeline, knowledge, relationships, and continuity gate

**Files:**
- Create: `app/continuity.py`
- Modify: `app/simulation.py`
- Modify: `app/historian.py`
- Test: `tests/test_continuity.py`

- [ ] เขียน tests ลำดับเวลา ความรู้ของตัวละคร และเผ่าใหม่ที่ยังไม่มีเบาะแส
- [ ] เพิ่ม `validate_event_continuity()` และการบันทึกผลกระทบถาวร
- [ ] ส่งบริบทความรู้/ความสัมพันธ์/กฎโลกเข้า simulation และ historian
- [ ] ให้ validation failure retry แบบจำกัดและ fallback เป็น warning
- [ ] รัน focused tests และ regression tests
- [ ] Commit: `feat: enforce narrative continuity`

### Task 4: Render fantasy metadata in web exports

**Files:**
- Modify: `app/export_html.py`
- Modify: `chronicle/reader/index.html` (ถ้าตัว export สร้างไฟล์นี้)
- Test: `tests/test_export_fantasy.py`

- [ ] เขียน tests ว่าหน้าโปรไฟล์แสดงข้อมูลแฟนตาซีเป็นไทย
- [ ] เพิ่มส่วนเผ่า ธาตุ เวท จุดอ่อน ต้นทุน และสถานะ discovered
- [ ] คงการเรียงตัวละครตามบท/การมีส่วนร่วมและฟังก์ชันขยายภาพ
- [ ] รัน export tests และตรวจ HTML ที่สร้างจริง
- [ ] Commit: `feat: render fantasy metadata in reader`

### Task 5: Full verification and deployment preparation

**Files:**
- Modify: `README.md` or `DEPLOY.md` เฉพาะส่วนคำสั่งใหม่
- Test: full `tests/`

- [ ] รัน `pytest -q`
- [ ] รัน simulation/spawn/export smoke tests ด้วย Python runtime ของ workspace
- [ ] ตรวจ `git diff`, สถานะ working tree และ generated output
- [ ] อัปเดตเอกสารคำสั่งรัน/ดีพอย
- [ ] Commit รวม verification และเตรียม push/deploy
