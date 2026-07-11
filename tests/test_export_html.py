from app import export_html
from app import config


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
