from app import config, db, export_html
from pathlib import Path
from scripts import rewrite_canonical_opening


def test_committed_public_index_has_no_world_reset_control():
    index = (Path(__file__).resolve().parents[1] / "chronicle" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'id="btn-reset"' not in index
    assert "triggerReset" not in index


def test_character_profile_uses_chronicle_dark_gold_theme(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    path = export_html.export_character_profile(
        {
            "name": "A",
            "status": "Alive",
            "faction": "Test",
            "special_power": "",
            "meta_data": "{}",
        },
        [],
    )
    html = path.read_text(encoding="utf-8")

    assert "background: #090a0f" in html
    assert "color: #d4af37" in html
    assert "#f7f4ef" not in html
    assert "#ebdcc5" not in html
    assert "#d4c2a8" not in html


def test_public_index_has_no_world_reset_control(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    path = export_html.rebuild_index([])
    html = path.read_text(encoding="utf-8")

    assert 'id="btn-reset"' not in html
    assert "triggerReset" not in html


def test_export_contains_viewport(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    path = export_html.export_chapter({
        "round_num": 1,
        "title": "ท",
        "body": "ย่อหน้าหนึ่ง\n\nย่อหน้าสอง",
        "location": "สภา",
        "p1_name": "A",
        "p2_name": "B",
    })
    html = path.read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert "ท" in html


def test_canonical_opening_rewrites_existing_chapter_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()
    for round_num in (10, 20, 30):
        db.save_chapter(round_num, f"Old {round_num}", "Old body", "Hall", "A", "B")

    rewrite_canonical_opening.rewrite_opening()

    assert db.get_chapter_by_round(10)["title"] == "บทที่ 1: เพลิงใต้บัลลังก์"
    assert "ผลึกบันทึกภาพ" in db.get_chapter_by_round(10)["body"]
    assert db.get_chapter_by_round(20)["title"] == "บทที่ 2: คำสัตย์และบัลลังก์ว่าง"
    assert db.get_chapter_by_round(30)["title"] == "บทที่ 3: ตลาดมืดของผู้รอดชีวิต"
    assert (config.CHRONICLE_DIR / "chapter-010.html").exists()
    assert (config.CHRONICLE_DIR / "chapter-020.html").exists()
    assert (config.CHRONICLE_DIR / "chapter-030.html").exists()


def test_exported_index_has_no_replacement_question_mark_text(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)

    html = export_html.rebuild_index([]).read_text(encoding="utf-8")

    assert "????" not in html


def test_index_always_labels_chapter_number(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    html = export_html.rebuild_index([
        {"round_num": 10, "title": "บทที่ 1: เปิดเรื่อง"},
        {"round_num": 40, "title": "การเปิดเผยความจริง"},
    ]).read_text(encoding="utf-8")
    assert "บทที่ 1: เปิดเรื่อง" in html
    assert "บทที่ 2: การเปิดเผยความจริง" in html


def test_chapter_page_uses_sequential_number_not_llm_title_number(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    monkeypatch.setattr(export_html.db, "list_chapters", lambda: [
        {"round_num": 3, "title": "บทที่ 1: เปิดเรื่อง"},
        {"round_num": 6, "title": "บทที่ 9: ฝ่ายการเมือง"},
    ])
    path = export_html.export_chapter({"round_num": 6, "title": "บทที่ 9: ฝ่ายการเมือง", "body": "เนื้อหา", "location": "สภา", "p1_name": "A", "p2_name": "B"})
    rendered = path.read_text(encoding="utf-8")
    assert "บทที่ 2: ฝ่ายการเมือง" in rendered
    assert "บทที่ 9: ฝ่ายการเมือง" not in rendered


def test_character_picker_sorts_by_participation_and_shows_count(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    monkeypatch.setattr(export_html, "list_all_characters", lambda: [
        {"name": "น้อย", "appearances": 1},
        {"name": "มาก", "appearances": 4},
    ])
    rendered = export_html.rebuild_index([]).read_text(encoding="utf-8")
    assert rendered.index("มาก — ร่วม 4 บท") < rendered.index("น้อย — ร่วม 1 บท")


def test_character_spotlight_includes_status(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    name = db.get_alive_characters()[0][0]
    db.update_character_status(name, "Dead")

    assert db.get_character_spotlight(name)["status"] == "Dead"


def test_repair_image_prompt_descriptions_removes_replacement_text(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    name = db.get_alive_characters()[0][0]
    db.add_character_image_prompt(name, "portrait", "????")

    db.repair_image_prompt_descriptions()

    prompts = db.parse_meta_data(db.get_character(name)["meta_data"])["image_prompts"]
    assert prompts[-1]["desc"] == "เหตุการณ์ใหม่"


def test_character_profile_export_uses_thai_status_and_fallbacks(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    db.init_db()
    name = "โนวา"
    db.insert_character(name, "Faction", "Personality", "Power")
    db.update_character_status(name, "Dead")

    char = db.get_character(name)
    path = export_html.export_character_profile(char, db.get_character_logs(name))
    rendered = path.read_text(encoding="utf-8")

    assert "เสียชีวิต" in rendered
    assert "Dead" not in rendered
    assert "ข้อมูลยังไม่ระบุ" in rendered
    assert ">-<" not in rendered


def test_index_localizes_relationship_type(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    db.init_db()
    db.update_relationship("จักรพรรดิไรเซน", "แม่ทัพหญิงวาเลเรีย", "trust_broken", "เหตุผล")

    rendered = export_html.rebuild_index([]).read_text(encoding="utf-8")

    assert "ความไว้วางใจพังทลาย" in rendered
    assert "trust_broken" not in rendered


def test_export_all_characters_removes_stale_profile_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    db.init_db()
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    stale = config.CHRONICLE_DIR / "char-deadbeef.html"
    stale.write_text("stale", encoding="utf-8")

    export_html.export_all_characters()

    assert not stale.exists()


def test_chapter_portrait_prompt_includes_character_sheet_anchors(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    db.init_db()
    name = db.get_alive_characters()[0][0]
    path = export_html.export_chapter({"round_num": 1, "title": "à¸—", "body": name, "location": "à¸ªà¸ à¸²", "p1_name": name, "p2_name": "à¸ˆà¸±à¸à¸£à¸žà¸£à¸£à¸”à¸´à¹„à¸£à¹€à¸‹à¸™"})
    rendered = path.read_text(encoding="utf-8")
    assert "<html" in rendered


def test_portrait_prompt_uses_unambiguous_english_gender_tokens():
    male = export_html._portrait_prompt("à¸¥à¸¹à¸„à¸±à¸ª", {"gender": "\u0e0a\u0e32\u0e22"}, "Alive", "portrait")
    female = export_html._portrait_prompt("à¸§à¸²à¹€à¸¥à¹€à¸£à¸µà¸¢", {"gender": "\u0e2b\u0e0d\u0e34\u0e07"}, "Alive", "portrait")
    assert "1boy" in male and "male" in male
    assert "1girl" in female and "female" in female


def test_portrait_prompt_includes_all_visual_character_status_fields():
    prompt = export_html._portrait_prompt(
        "à¸§à¸²à¹€à¸¥à¹€à¸£à¸µà¸¢",
        {"gender": "\u0e2b\u0e0d\u0e34\u0e07", "age": "35 à¸›à¸µ", "race": "à¸¡à¸™à¸¸à¸©à¸¢à¹Œ", "title": "à¹à¸¡à¹ˆà¸—à¸±à¸ž", "faction": "à¸£à¸²à¸Šà¸ªà¸³à¸™à¸±à¸à¹€à¸à¹ˆà¸²", "height": "170 à¸‹à¸¡.", "weight": "65 à¸à¸.", "skin_color": "à¸œà¸´à¸§à¸ªà¸­à¸‡à¸ªà¸µ", "weapon": "à¸”à¸²à¸šà¸ªà¸±à¹‰à¸™"},
        "Alive",
        "portrait",
    )
    for value in ("35 à¸›à¸µ", "à¸¡à¸™à¸¸à¸©à¸¢à¹Œ", "à¸£à¸²à¸Šà¸ªà¸³à¸™à¸±à¸à¹€à¸à¹ˆà¸²", "170 à¸‹à¸¡.", "65 à¸à¸.", "à¸œà¸´à¸§à¸ªà¸­à¸‡à¸ªà¸µ", "à¸”à¸²à¸šà¸ªà¸±à¹‰à¸™"):
        assert value in prompt


def test_portrait_prompt_removes_gender_conflicts_from_model_prompt():
    female = export_html._portrait_prompt("à¸§à¸²à¹€à¸¥à¹€à¸£à¸µà¸¢", {"gender": "\u0e2b\u0e0d\u0e34\u0e07"}, "Alive", "female warrior, male face, 1boy")
    male = export_html._portrait_prompt("à¸¥à¸¹à¸„à¸±à¸ª", {"gender": "\u0e0a\u0e32\u0e22"}, "Alive", "male warrior, female face, 1girl")
    assert "male face" not in female.lower() and "1boy" not in female.lower()
    assert "female face" not in male.lower() and "1girl" not in male.lower()


def test_portrait_prompt_makes_age_visible_for_mature_characters():
    prompt = export_html._portrait_prompt("à¸”à¸±à¸ªà¹€à¸‹à¸­à¸£à¹Œ", {"gender": "\u0e0a\u0e32\u0e22", "age": "42 à¸›à¸µ"}, "Alive", "young handsome man")
    assert "42-year-old" in prompt
    assert "mature adult" in prompt
    assert "young" not in prompt.lower()
