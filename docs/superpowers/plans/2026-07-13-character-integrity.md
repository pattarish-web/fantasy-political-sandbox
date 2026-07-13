# Character Integrity and Thai Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เติมข้อมูลตัวละครให้ครบ แปลค่าที่ผู้เล่นเห็นเป็นไทย และซ่อมชื่ออ้างอิงที่ทำให้ประวัติแยกจากโปรไฟล์

**Architecture:** เพิ่มโมดูล `app/character_data.py` เป็นขอบเขต normalization/backfill/label mapping แล้วเรียกจาก DB migration, spawn parser และ static exporter. ข้อมูล canonical ใช้ชื่อเต็มในฐานข้อมูล ส่วน alias เก่าถูกย้ายใน migration เดียวแบบ idempotent.

**Tech Stack:** Python 3, sqlite3, Pydantic, pytest, static HTML export

## Global Constraints

- ข้อมูลที่ผู้เล่นเห็นต้องเป็นภาษาไทย; image-generation prompts ยังคงเป็นภาษาอังกฤษได้
- normalization เติมเฉพาะค่าที่ว่าง และต้องทำซ้ำได้โดยไม่เพิ่มแถวหรือความสัมพันธ์ซ้ำ
- ห้ามลบ log/บทเดิมเพื่อแก้ชื่อ
- ทดสอบด้วย bundled Python และ `pytest -q`

---

### Task 1: Character data normalization contract

**Files:**
- Create: `app/character_data.py`
- Test: `tests/test_character_data.py`

- [ ] เขียน failing tests สำหรับ `normalize_meta`, `normalize_display_value`, `canonicalize_character_name` โดยตรวจค่ามาตรฐาน, fallback ภาษาไทย, alias นราอำพัน และไม่แปล `image_prompt`
- [ ] รัน `pytest tests/test_character_data.py -q` และยืนยันว่า fail เพราะโมดูล/ฟังก์ชันยังไม่มี
- [ ] เพิ่ม `PROFILE_FIELDS`, `STAT_FIELDS`, `CHARACTER_PROFILE_BACKFILL`, alias map, gender/sexuality/unit mappings และ helper ที่เติมเฉพาะ key ว่าง
- [ ] รัน test เดิมให้ผ่าน
- [ ] commit `feat: add character profile normalization contract`

### Task 2: Database migration and reference repair

**Files:**
- Modify: `app/db.py:41-150, 462-490, 528-550`
- Test: `tests/test_db.py`

- [ ] เพิ่ม failing tests ที่สร้าง alias log/relationship และตัวละคร incomplete แล้วเรียก `init_db()`; คาดหวัง metadata ครบ, ชื่อถูก canonicalize และเรียกซ้ำแล้วไม่เปลี่ยนเพิ่ม
- [ ] รัน test เฉพาะรายการและยืนยัน fail
- [ ] ให้ `init_db()` และ `reset_world_state()` เรียก repair หลัง seed; ให้ `insert_character()` normalize metadata; ให้ `save_log()` และ `update_relationship()` canonicalize participant names
- [ ] ซ่อม `logs`, `chapters`, `relationships`, `artifacts` ใน transaction เดียวโดยใช้ alias mapและไม่ลบข้อมูล
- [ ] รัน test เฉพาะรายการและ `pytest tests/test_db.py -q`
- [ ] commit `feat: repair character metadata and references`

### Task 3: Strict spawn contract

**Files:**
- Modify: `app/schemas.py:64-89`, `app/spawn.py:24-110`
- Test: `tests/test_spawn.py`

- [ ] เพิ่ม failing tests ว่า payload ขาด `race`, `age`, `skills`, `weapon`, `ambition`, `flaw` หรือ stat ใด ๆ ต้องถูกปฏิเสธ และ payload ครบต้องเก็บ metadata ครบ
- [ ] รัน `pytest tests/test_spawn.py -q` และยืนยัน fail
- [ ] เปลี่ยน field ที่หน้าโปรไฟล์ใช้เป็น required, จำกัด stat 1-100, ให้ prompt ระบุภาษาไทยและ field ครบ, และใช้ normalization ก่อน insert
- [ ] รัน test spawn และชุด test ทั้งหมด
- [ ] commit `feat: require complete generated character profiles`

### Task 4: Thai static export

**Files:**
- Modify: `app/export_html.py:158-205, 300-320, 448-455, 830-895`
- Test: `tests/test_export_html.py`

- [ ] เพิ่ม failing tests ว่า profile HTML ไม่มี raw `Alive`, `Dead`, relationship keys หรือ `-` ใน metadata และมีป้ายไทย
- [ ] รัน test และยืนยัน fail
- [ ] เพิ่ม label maps สำหรับ status/relationship/stat labels, ใช้ fallback ไทย และ canonicalize values ก่อน escape; คง English เฉพาะ URL/prompt/CSS
- [ ] รัน export tests และชุด test ทั้งหมด
- [ ] commit `feat: localize character chronicle output`

### Task 5: Repair live DB, export, verify, deploy

**Files:**
- Modify: `data/world.db`, `chronicle/`
- Use: `scripts/rewrite_canonical_opening.py`

- [ ] รัน migration/export script ใน worktree และตรวจ inventory ว่า 16 ตัวไม่มี missing profile fields และไม่มี broken references
- [ ] รัน `pytest -q` และตรวจ `rg` ใน `chronicle` สำหรับ raw relationship/status leaks
- [ ] commit generated DB/static pages
- [ ] merge branch เข้า `master`, push, ตรวจ GitHub Actions deployment และเปิด URL ตรวจผล
