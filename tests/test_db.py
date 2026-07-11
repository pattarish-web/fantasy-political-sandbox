import json

import app.config as config
from app import db


def test_init_seeds_characters(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    alive = db.get_alive_characters()
    assert len(alive) == 20


def test_save_log_and_latest_round(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    name = db.get_alive_characters()[0][0]
    db.save_log(1, "วิหาร", name, "B", "hi", "ok", 1)
    assert db.get_latest_round() == 1
    assert db.get_character_spotlight(name)["appearances"] == 1


def test_undrafted_drama_and_chapter(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    db.save_log(2, "สภา", "A", "B", "d", "c", 1)
    row = db.get_latest_undrafted_drama()
    assert row[0] == 2
    db.save_chapter(2, "ชื่อตอน", "เนื้อเรื่อง", "สภา", "A", "B")
    assert db.get_latest_undrafted_drama() is None
    assert db.get_chapter_by_round(2)["title"] == "ชื่อตอน"


def test_insert_character_grows_world(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    assert db.insert_character("โนวา", "กบฏ/มนุษย์", "นักข่าว", "[พลัง - แสง] เรืองแสง")
    assert db.count_alive() == 21
    assert db.insert_character("โนวา", "x", "y", "z") is False
