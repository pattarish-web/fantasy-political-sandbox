import json

from app import config, db, simulation


def test_run_simulation_round_saves_log(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    payload = {
        "dialogue": "a: hi\nb: bye",
        "consequence": "nothing",
        "is_drama": 0,
        "character_killed": None,
    }
    monkeypatch.setattr(
        simulation,
        "call_gemini",
        lambda prompt, as_json=False: json.dumps(payload),
    )
    result = simulation.run_simulation_round()
    assert "error" not in result
    assert result["round_num"] == 1
    assert db.get_latest_round() == 1
