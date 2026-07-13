from pathlib import Path


def test_auto_workflow_fails_when_historian_returns_error():
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "auto.yml").read_text(encoding="utf-8")

    assert "python scripts/run_historian.py" in workflow
    assert 'python -c "from app.historian import run_historian' not in workflow
