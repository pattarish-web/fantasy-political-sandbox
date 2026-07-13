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
        "call_llm",
        lambda prompt, response_schema=None: json.dumps(
            {"title": "บททดสอบ", "body": "เนื้อหา", "tone": "neutral"}
        ),
    )
    result = historian.run_historian()
    assert result["title"] == "บททดสอบ"
    assert db.get_chapter_by_round(3) is not None
    assert (config.CHRONICLE_DIR / "chapter-003.html").exists()


def test_historian_selects_three_events_without_echoing_them_as_context(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()
    for round_num in range(1, 5):
        db.save_log(round_num, "Hall", "A", "B", f"d{round_num}", f"c{round_num}", 1)
    captured_prompts = []
    monkeypatch.setattr(
        historian,
        "call_llm",
        lambda prompt, response_schema=None: (
            captured_prompts.append(prompt)
            or json.dumps({"title": "Chapter", "body": "New story", "tone": "neutral"})
        ),
    )

    result = historian.run_historian()

    prompt = captured_prompts[0]
    earlier_context = prompt.split("[Earlier world context]")[1].split("[Canonical story state]")[0]
    assert result["round_num"] == 3
    assert "Event 1" in prompt
    assert "Event 3" in prompt
    assert "Event 4" not in prompt
    assert "Event 1" not in earlier_context
    assert [log["round_num"] for log in db.get_undrafted_logs(limit=3)] == [4]


def test_historian_rejects_canon_dead_character_acting_in_present(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()
    db.save_story_state({"deaths": ["A"]})
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    monkeypatch.setattr(
        historian,
        "call_llm",
        lambda prompt, response_schema=None: json.dumps(
            {"title": "Chapter", "body": "A ยืนขึ้นและออกคำสั่ง", "tone": "neutral"}
        ),
    )

    result = historian.run_historian()

    assert "error" in result
    assert db.get_chapter_by_round(1) is None


def test_historian_rejects_reused_dialogue_from_previous_chapter(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()
    repeated_quote = '"ประโยคเดิมที่ยาวพอให้ระบบตรวจจับได้อย่างแน่นอน"'
    db.save_chapter(0, "Previous", repeated_quote, "Hall", "A", "B")
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    monkeypatch.setattr(
        historian,
        "call_llm",
        lambda prompt, response_schema=None: json.dumps(
            {"title": "Chapter", "body": repeated_quote, "tone": "neutral"}
        ),
    )

    result = historian.run_historian()

    assert "error" in result
    assert db.get_chapter_by_round(1) is None


def test_published_death_is_sent_to_next_historian_as_canon(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()
    db.save_log(
        1,
        "Hall",
        "A",
        "B",
        "d",
        "A dies",
        1,
        {"character_killed": "A"},
    )
    captured_prompts = []
    monkeypatch.setattr(
        historian,
        "call_llm",
        lambda prompt, response_schema=None: (
            captured_prompts.append(prompt)
            or json.dumps({"title": "Chapter", "body": "A consequence", "tone": "tragic"})
        ),
    )

    historian.run_historian()
    db.save_log(2, "Hall", "B", "C", "d", "A political response", 1)
    historian.run_historian()

    assert '"deaths": ["A"]' in captured_prompts[1]
