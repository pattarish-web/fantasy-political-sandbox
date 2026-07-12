from pathlib import Path


def test_workflows_share_world_state_and_publish_pages():
    root = Path(__file__).resolve().parents[1]
    auto = (root / ".github" / "workflows" / "auto.yml").read_text(encoding="utf-8")
    historian = (root / ".github" / "workflows" / "historian.yml").read_text(encoding="utf-8")
    simulate = (root / ".github" / "workflows" / "simulate.yml").read_text(encoding="utf-8")

    assert "concurrency:" in auto
    assert "group: world-state" in auto
    assert "actions/configure-pages@v5" in auto
    assert "actions/upload-pages-artifact@v3" in auto
    assert "actions/deploy-pages@v4" in auto

    assert "concurrency:" in historian
    assert "group: world-state" in historian
    assert "actions/configure-pages@v5" in historian
    assert "actions/upload-pages-artifact@v3" in historian
    assert "actions/deploy-pages@v4" in historian

    assert "concurrency:" in simulate
    assert "group: world-state" in simulate
