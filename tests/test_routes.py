from app import config
from app import create_app


def test_status_and_simulate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "APP_PASSWORD", "")
    app = create_app()
    monkeypatch.setattr(
        "app.routes.run_simulation_round",
        lambda: {
            "round_num": 1,
            "location": "x",
            "chars": "a VS b",
            "dialogue": "d",
            "consequence": "c",
            "is_drama": 0,
        },
    )
    client = app.test_client()
    s = client.get("/api/status").get_json()
    assert "alive" in s
    r = client.post("/api/simulate")
    assert r.status_code == 200
    assert r.get_json()["round_num"] == 1
