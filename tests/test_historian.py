import json

from app import config, db, historian


def test_historian_writes_chapter(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()
    db.save_log(3, "สลัม", "A", "B", "d", "c", 1)
    monkeypatch.setattr(
        historian,
        "call_gemini",
        lambda prompt, as_json=False: json.dumps(
            {"title": "บททดสอบ", "body": "เนื้อหา"}
        ),
    )
    result = historian.run_historian()
    assert result["title"] == "บททดสอบ"
    assert db.get_chapter_by_round(3) is not None
    assert (config.CHRONICLE_DIR / "chapter-003.html").exists()
