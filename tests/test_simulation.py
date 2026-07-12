import json

from app import config, db, simulation


def _seed_characters():
    db.insert_character("A", "F1", "brave", "power one")
    db.insert_character("B", "F2", "wise", "power two")


def test_run_simulation_batch_saves_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    _seed_characters()
    payload = {
        "encounters": [
            {
                "p1_name": "A",
                "p2_name": "B",
                "location": "ป่า",
                "dialogue": "a: hi\nb: bye",
                "consequence": "nothing",
                "is_drama": 0,
                "character_killed": None,
            }
        ]
    }
    monkeypatch.setattr(simulation, "RANDOM_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(simulation, "DRAMA_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(
        simulation,
        "call_llm",
        lambda prompt, response_schema=None: json.dumps(payload),
    )
    monkeypatch.setattr(simulation, "export_updated_characters", lambda chars: None)

    result = simulation.run_simulation_batch(1)

    assert "error" not in result
    assert result["events_processed"] == 1
    assert db.get_latest_round() == 1
    assert result.get("born") == []


def test_simulation_can_birth_character(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    _seed_characters()
    payload = {
        "encounters": [
            {
                "p1_name": "A",
                "p2_name": "B",
                "location": "ป่า",
                "dialogue": "a: hi\nb: bye",
                "consequence": "nothing",
                "is_drama": 0,
                "character_killed": None,
            }
        ]
    }
    monkeypatch.setattr(simulation, "RANDOM_SPAWN_CHANCE", 1.0)
    monkeypatch.setattr(simulation, "DRAMA_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(
        simulation,
        "call_llm",
        lambda prompt, response_schema=None: json.dumps(payload),
    )
    def fake_generate_character(**kwargs):
        db.insert_character(
            "ไลร่า",
            "กบฏ/เอลฟ์",
            "สายลับ",
            "[พลัง - เงา] ซ่อนตัว",
        )
        return {
            "name": "ไลร่า",
            "faction": "กบฏ/เอลฟ์",
            "personality": "สายลับ",
            "special_power": "[พลัง - เงา] ซ่อนตัว",
        }

    monkeypatch.setattr(simulation, "generate_character", fake_generate_character)
    monkeypatch.setattr(simulation, "export_updated_characters", lambda chars: None)
    before = db.count_alive()

    result = simulation.run_simulation_batch(1)

    assert "error" not in result
    assert any(b["name"] == "ไลร่า" for b in result["born"])
    assert db.count_alive() == before + 1
