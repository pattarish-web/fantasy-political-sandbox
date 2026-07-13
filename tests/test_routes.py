from app import config, create_app
from pathlib import Path


def test_dashboard_template_has_no_world_reset_control():
    template = (
        Path(__file__).resolve().parents[1] / "templates" / "mobile_dashboard.html"
    ).read_text(encoding="utf-8")

    assert 'id="btnReset"' not in template
    assert "triggerReset" not in template


def test_status_is_public_and_mutations_require_exact_header(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "APP_PASSWORD", "secret")
    app = create_app()
    monkeypatch.setattr(
        "app.routes.run_simulation_batch",
        lambda batch_size: {"status": "ok", "batch_size": batch_size},
    )
    monkeypatch.setattr("app.routes.run_historian", lambda: {"title": "chapter"})

    client = app.test_client()

    assert client.get("/api/status").status_code == 200
    assert client.post("/api/simulate").status_code == 403
    assert client.post("/api/historian").status_code == 403

    ok = client.post("/api/simulate", headers={"X-App-Password": "secret"})
    assert ok.status_code == 200
    assert ok.get_json()["batch_size"] == 1

    assert client.post("/api/historian", headers={"X-App-Password": "bad"}).status_code == 403
