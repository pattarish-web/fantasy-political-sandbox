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


def test_minor_encounters_do_not_add_gallery_prompts(tmp_path, monkeypatch):
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
                "consequence": "small talk",
                "is_drama": 0,
                "character_killed": None,
                "power_awakened": None,
                "artifact_event": None,
                "war_declaration": None,
                "relationship_update": None,
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

    simulation.run_simulation_batch(1)

    a_meta = db.get_character("A")["meta_data"]
    assert json.loads(a_meta).get("image_prompts", []) == []


def test_major_events_add_gallery_prompts(tmp_path, monkeypatch):
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
                "consequence": "major event",
                "is_drama": 1,
                "character_killed": "A",
                "power_awakened": {"character_name": "B", "new_power": "Storm"},
                "artifact_event": None,
                "war_declaration": None,
                "relationship_update": None,
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

    simulation.run_simulation_batch(1)

    a_meta = json.loads(db.get_character("A")["meta_data"])
    b_meta = json.loads(db.get_character("B")["meta_data"])
    assert len(a_meta.get("image_prompts", [])) == 1
    assert len(b_meta.get("image_prompts", [])) == 1


def test_simulation_rejects_dead_character_without_saving_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    _seed_characters()
    db.update_character_status("A", "Dead")
    monkeypatch.setattr(simulation, "RANDOM_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(
        simulation,
        "call_llm",
        lambda prompt, response_schema=None: json.dumps(
            {
                "encounters": [
                    {
                        "p1_name": "A",
                        "p2_name": "B",
                        "location": "Hall",
                        "dialogue": "A speaks",
                        "consequence": "A returns",
                        "is_drama": 1,
                    }
                ]
            }
        ),
    )

    result = simulation.run_simulation_batch(1)

    assert "error" in result
    assert db.get_latest_round() == 0


def test_simulation_rejects_nonparticipant_death_without_saving_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    _seed_characters()
    monkeypatch.setattr(simulation, "RANDOM_SPAWN_CHANCE", 0.0)
    monkeypatch.setattr(
        simulation,
        "call_llm",
        lambda prompt, response_schema=None: json.dumps(
            {
                "encounters": [
                    {
                        "p1_name": "A",
                        "p2_name": "B",
                        "location": "Hall",
                        "dialogue": "A speaks",
                        "consequence": "C dies",
                        "is_drama": 1,
                        "character_killed": "C",
                    }
                ]
            }
        ),
    )

    result = simulation.run_simulation_batch(1)

    assert "error" in result
    assert db.get_latest_round() == 0
