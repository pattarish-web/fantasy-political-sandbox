from app import export_html
from app import config
from pathlib import Path


def test_committed_public_index_has_no_world_reset_control():
    index = (Path(__file__).resolve().parents[1] / "chronicle" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'id="btn-reset"' not in index
    assert "triggerReset" not in index


def test_public_index_has_no_world_reset_control(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    path = export_html.rebuild_index([])
    html = path.read_text(encoding="utf-8")

    assert 'id="btn-reset"' not in html
    assert "triggerReset" not in html


def test_export_contains_viewport(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    path = export_html.export_chapter({
        "round_num": 1,
        "title": "ท",
        "body": "ย่อหน้าหนึ่ง\n\nย่อหน้าสอง",
        "location": "สภา",
        "p1_name": "A",
        "p2_name": "B",
    })
    html = path.read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert "ท" in html
