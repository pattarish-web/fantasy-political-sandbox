import json

import json
import sqlite3

import app.config as config
from app import db, narrative


def test_init_seeds_characters(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    alive = db.get_alive_characters()
    assert len(alive) == 8


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
    assert db.insert_character("โนวา", "กบฏ/มนุษย์", "นักข่าว", "[พลัง - แสง] เรื่องแสง")
    assert db.count_alive() == 9
    assert db.insert_character("โนวา", "x", "y", "z") is False


def test_story_state_defaults_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()

    assert db.get_story_state()["deaths"] == []

    db.save_story_state({"deaths": ["A"], "resolved_events": ["round:1"]})

    state = db.get_story_state()
    assert state["deaths"] == ["A"]
    assert state["resolved_events"] == ["round:1"]
    assert state["open_threads"] == []


def test_story_state_backfills_existing_world_when_no_ledger_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    db.insert_character("A", "Faction", "Personality", "Power")
    db.update_character_status("A", "Dead")
    db.save_chapter(1, "Chapter", "Body", "Hall", "A", "B")

    state = db.get_story_state()

    assert state["deaths"] == ["A"]
    assert state["resolved_events"] == ["round:1"]


def test_undrafted_logs_are_limited_and_keep_story_facts(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    for round_num in range(1, 5):
        db.save_log(
            round_num,
            "Hall",
            "A",
            "B",
            "d",
            "c",
            1,
            {"character_killed": "A" if round_num == 1 else None},
        )

    logs = db.get_undrafted_logs(limit=3)

    assert [log["round_num"] for log in logs] == [1, 2, 3]
    assert logs[0]["story_facts"]["character_killed"] == "A"


def test_save_chapter_persists_story_state_in_the_same_operation(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()

    db.save_chapter(
        1,
        "Chapter",
        "Body",
        "Hall",
        "A",
        "B",
        story_state={"deaths": ["A"], "resolved_events": ["round:1"]},
    )

    assert db.get_chapter_by_round(1)["title"] == "Chapter"
    assert db.get_story_state()["deaths"] == ["A"]


def test_story_state_preserves_typed_facts_and_faction_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()

    db.save_story_state(
        {
            "relationship_changes": [{"round_num": 1, "type": "schism"}],
            "faction_ledger": {"จักรวรรดิเหล็กกล้า": {"pressure": "สูง"}},
        }
    )

    state = db.get_story_state()

    assert state["relationship_changes"] == [{"round_num": 1, "type": "schism"}]
    assert state["faction_ledger"]["จักรวรรดิเหล็กกล้า"]["pressure"] == "สูง"


def test_world_bible_explains_magitech_and_political_stakes():
    bible = narrative.format_world_bible()

    assert "เวทกล" in bible
    assert "จักรวรรดิเหล็กกล้า" in bible
    assert "ภาคีจอมเวทศักดิ์สิทธิ์" in bible


def test_init_repairs_legacy_character_aliases_and_references(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute(
            "INSERT INTO characters (name, faction, personality, special_power, status, meta_data) VALUES (?, ?, ?, ?, ?, ?)",
            ("นราอำพัน (Nara-Amphan)", "Council of the Golden Lotus", "Calm mediator", "Whisper-Binding", "Alive", json.dumps({"gender": "female"})),
        )
        conn.execute(
            "INSERT INTO logs (round_num, location, p1_name, p2_name, dialogue_text, consequence, is_drama) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (99, "สภา", "แม่ทัพหญิงวาเลเรีย", "นราอำพัน", "ทดสอบ", "ทดสอบ", 0),
        )
        conn.execute(
            "INSERT INTO relationships (char1, char2, relationship_type, reason) VALUES (?, ?, ?, ?)",
            ("นราอำพัน", "แม่ทัพหญิงวาเลเรีย", "schism", "ทดสอบ"),
        )
        conn.commit()

    db.init_db()

    repaired = db.get_character("นราอำพัน")
    assert repaired is not None
    assert "นราอำพัน (Nara-Amphan)" not in db.list_character_names()
    assert db.parse_meta_data(repaired["meta_data"])["race"] == "มนุษย์"
    assert db.get_all_relationships()[0]["char1"] in {"นราอำพัน", "จักรพรรดิไรเซน", "อาร์คบิชอปโซลาร์", "ทวีป กฤษณะมิตร", "ปาริชาติ วีระกุล", "พ่อค้าอาวุธซาเคียน"}
    with sqlite3.connect(config.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM logs WHERE p2_name = 'นราอำพัน'").fetchone()[0] == 1


def test_insert_character_stores_complete_thai_profile_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    db.insert_character("โนวา", "Faction", "Personality", "Power")

    meta = db.parse_meta_data(db.get_character("โนวา")["meta_data"])
    assert meta["race"] == "ข้อมูลยังไม่ระบุ"
    assert all(meta[field] for field in ("gender", "age", "skills", "weapon", "ambition", "flaw"))
