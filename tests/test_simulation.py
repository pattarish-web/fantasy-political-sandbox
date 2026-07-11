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
    monkeypatch.setattr(simulation, "RANDOM_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(simulation, "DRAMA_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(
        simulation,
        "call_gemini",
        lambda prompt, as_json=False: json.dumps(payload),
    )
    result = simulation.run_simulation_round()
    assert "error" not in result
    assert result["round_num"] == 1
    assert db.get_latest_round() == 1
    assert result.get("born") == []


def test_simulation_can_birth_character(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    payload = {
        "dialogue": "a: hi\nb: bye",
        "consequence": "nothing",
        "is_drama": 0,
        "character_killed": None,
    }
    monkeypatch.setattr(simulation, "RANDOM_SPAWN_CHANCE", 1.0)
    monkeypatch.setattr(simulation, "DRAMA_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(
        simulation,
        "call_gemini",
        lambda prompt, as_json=False: json.dumps(payload),
    )
    monkeypatch.setattr(
        simulation,
        "generate_character",
        lambda **kwargs: {
            "name": "ไลร่า",
            "faction": "กบฏ/เอลฟ์",
            "personality": "สายลับ",
            "special_power": "[พลัง - เงา] ซ่อนตัว",
        },
    )
    before = db.count_alive()
    # generate_character mock does not insert — simulate insert in wrapper
    real_gen = None

    def fake_gen(**kwargs):
        db.insert_character("ไลร่า", "กบฏ/เอลฟ์", "สายลับ", "[พลัง - เงา] ซ่อนตัว")
        return {
            "name": "ไลร่า",
            "faction": "กบฏ/เอลฟ์",
            "personality": "สายลับ",
            "special_power": "[พลัง - เงา] ซ่อนตัว",
        }

    monkeypatch.setattr(simulation, "generate_character", fake_gen)
    result = simulation.run_simulation_round()
    assert "error" not in result
    assert any(b["name"] == "ไลร่า" for b in result["born"])
    assert db.count_alive() == before + 1
    assert "birth_notice" in result
