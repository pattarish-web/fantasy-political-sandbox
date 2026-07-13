import json

from app import config, db, historian
from app.schemas import ChapterCritique, ChapterPlan


VALID_BODY = "ความจริงทางการเมืองไม่เคยยอมจำนนต่อคำประกาศง่ายดาย" * 100


def _plan(rounds, povs=None, tone="epic"):
    return {
        "source_rounds": rounds,
        "pov_characters": povs or ["A"],
        "central_conflict": "คำสั่งของผู้มีอำนาจปะทะความรับผิดชอบต่อประชาชน",
        "political_stake": "ความชอบธรรมของรัฐบาลและความไว้ใจของกองทัพ",
        "choice": "ตัวละครต้องเลือกว่าคุ้มครองคำสั่งหรือชีวิตผู้บริสุทธิ์",
        "cost": "การเลือกนั้นทำให้สูญเสียพันธมิตรที่สำคัญ",
        "unresolved_thread": "เอกสารลับยังอยู่ในมือของฝ่ายตรงข้าม",
        "tone": tone,
    }


def _chapter(title="บททดสอบ", body=VALID_BODY, tone="epic"):
    return {"title": title, "body": body, "tone": tone}


def _critique(approved=True):
    return {
        "approved": approved,
        "blocking_issues": [] if approved else ["ความขัดแย้งยังไม่ชัดเจน"],
        "rewrite_brief": "ทำให้การตัดสินใจและราคาที่จ่ายชัดขึ้น" if not approved else "",
    }


def _configure_world(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()


def _sequence_fake(responses, captured_prompts):
    def fake(prompt, response_schema=None):
        captured_prompts.append((prompt, response_schema))
        return json.dumps(responses.pop(0), ensure_ascii=False)

    return fake


def test_spawned_character_is_in_historian_context():
    text, names = historian._format_selected_events([
        {
            "round_num": 1,
            "location": "Hall",
            "p1_name": "A",
            "p2_name": "B",
            "consequence": "c",
            "is_drama": 0,
            "dialogue_text": "d",
            "story_facts": {"character_spawned": {"name": "Nova"}},
        }
    ])
    assert "Nova" in names
    assert "character_spawned" in text


def test_historian_writes_validated_chapter(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    db.save_log(3, "สลัม", "A", "B", "d", "c", 1)
    responses = [_plan([3]), _chapter(), _critique()]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, []))

    result = historian.run_historian()

    assert result["title"] == "บททดสอบ"
    assert db.get_chapter_by_round(3) is not None
    assert (config.CHRONICLE_DIR / "chapter-003.html").exists()


def test_opening_stage_requires_world_context_for_first_chapter():
    assert historian._opening_contract(1)
    assert "world" in historian._opening_contract(1).lower()


def test_opening_contract_does_not_depend_on_empty_earlier_context(monkeypatch):
    plan = historian.ChapterPlan(**_plan([1]))
    captured = []
    monkeypatch.setattr(historian, "call_llm", lambda prompt, response_schema=None: captured.append(prompt) or json.dumps(_chapter()))
    historian._request_chapter(plan, "event", {"chapter_count": 0}, "characters", "existing context")
    assert "Opening structure contract" in captured[0]


def test_chapter_rewrite_defaults_missing_tone_to_approved_plan(monkeypatch):
    plan = historian.ChapterPlan(**_plan([1], tone="neutral"))
    monkeypatch.setattr(historian, "call_llm", lambda prompt, response_schema=None: json.dumps({"title": "t", "body": VALID_BODY}, ensure_ascii=False))
    assert historian._request_chapter(plan, "event", {}, "characters", "").tone == "neutral"


def test_story_state_tracks_emotional_arc():
    state = db._normalize_story_state({"emotional_arcs": [{"character": "A", "emotion": "fear"}]})
    assert state["emotional_arcs"] == [{"character": "A", "emotion": "fear"}]


def test_historian_selects_three_events_without_echoing_them_as_context(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    for round_num in range(1, 5):
        db.save_log(round_num, "Hall", "A", "B", f"d{round_num}", f"c{round_num}", 1)
    captured_prompts = []
    responses = [_plan([1, 2, 3]), _chapter(), _critique()]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, captured_prompts))

    result = historian.run_historian()

    prose_prompt = captured_prompts[1][0]
    earlier_context = prose_prompt.split("[Earlier world context]")[1].split("[Canonical story state]")[0]
    assert result["round_num"] == 3
    assert "Event 1" in prose_prompt
    assert "Event 3" in prose_prompt
    assert "Event 4" not in prose_prompt
    assert "Event 1" not in earlier_context
    assert [log["round_num"] for log in db.get_undrafted_logs(limit=3)] == [4]


def test_historian_rejects_canon_dead_character_acting_in_present(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    db.save_story_state({"deaths": ["A"]})
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    responses = [_plan([1]), _chapter(body="A ยืนขึ้นและออกคำสั่ง " + VALID_BODY)]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, []))

    result = historian.run_historian()

    assert "error" in result
    assert db.get_chapter_by_round(1) is None


def test_historian_rejects_reused_dialogue_from_previous_chapter(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    repeated_quote = '"ประโยคเดิมที่ยาวพอให้ระบบตรวจจับได้อย่างแน่นอน"'
    db.save_chapter(0, "Previous", repeated_quote, "Hall", "A", "B")
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    responses = [_plan([1]), _chapter(body=repeated_quote + VALID_BODY)]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, []))

    result = historian.run_historian()

    assert "error" in result
    assert db.get_chapter_by_round(1) is None


def test_published_death_is_sent_to_next_historian_as_canon(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    db.save_log(1, "Hall", "A", "B", "d", "A dies", 1, {"character_killed": "A"})
    captured_prompts = []
    responses = [_plan([1]), _chapter(), _critique()]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, captured_prompts))

    historian.run_historian()
    db.save_log(2, "Hall", "B", "C", "d", "A political response", 1)
    responses.extend([_plan([2], ["B"]), _chapter(title="บทสอง"), _critique()])
    historian.run_historian()

    assert '"deaths": ["A"]' in captured_prompts[4][0]


def test_historian_rejects_plan_with_unselected_round(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    responses = [_plan([99])]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, []))

    result = historian.run_historian()

    assert result["error"] == "Plan uses wrong source rounds"
    assert db.get_chapter_by_round(1) is None


def test_historian_rewrites_once_after_blocking_critique(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    captured_prompts = []
    responses = [
        _plan([1]),
        _chapter(title="ร่างแรก"),
        _critique(approved=False),
        _chapter(title="ฉบับแก้"),
        _critique(approved=True),
    ]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, captured_prompts))

    result = historian.run_historian()

    assert result["title"] == "ฉบับแก้"
    assert len(captured_prompts) == 5


def test_historian_rejects_body_outside_thai_character_bounds(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    responses = [_plan([1]), _chapter(body="สั้นเกินไป")]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, []))

    result = historian.run_historian()

    assert result["error"] == "Chapter body is outside the allowed Thai character range"


def test_historian_uses_structured_plan_and_critique_schemas(tmp_path, monkeypatch):
    _configure_world(tmp_path, monkeypatch)
    db.save_log(1, "Hall", "A", "B", "d", "c", 1)
    captured_prompts = []
    responses = [_plan([1]), _chapter(), _critique()]
    monkeypatch.setattr(historian, "call_llm", _sequence_fake(responses, captured_prompts))

    historian.run_historian()

    assert captured_prompts[0][1] is ChapterPlan
    assert captured_prompts[2][1] is ChapterCritique
