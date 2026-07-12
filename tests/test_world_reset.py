from pathlib import Path

import app.config as config
from app import db
from app import world_reset


def test_reset_world_reseeds_and_clears_exports(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    (config.CHRONICLE_DIR / "chapter-001.html").write_text("old", encoding="utf-8")
    (config.ROOT / "story_summary.json").write_text("old", encoding="utf-8")

    db.init_db()
    db.save_log(1, "ป่า", "A", "B", "hi", "ok", 1)
    db.save_chapter(1, "old", "body", "ป่า", "A", "B")
    db.insert_character("ชั่วคราว", "F", "p", "pow")

    result = world_reset.reset_world()

    assert result["characters"] == 8
    assert result["logs"] == 0
    assert result["chapters"] == 0
    assert not (config.CHRONICLE_DIR / "chapter-001.html").exists()
    assert not (config.ROOT / "story_summary.json").exists()
    assert db.get_latest_round() == 0
    assert db.get_chapter_by_round(1) is None
