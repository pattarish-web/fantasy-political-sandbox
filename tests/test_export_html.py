from app import config, db, export_html
from pathlib import Path
from scripts import rewrite_canonical_opening


def test_committed_public_index_has_no_world_reset_control():
    index = (Path(__file__).resolve().parents[1] / "chronicle" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'id="btn-reset"' not in index
    assert "triggerReset" not in index


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
