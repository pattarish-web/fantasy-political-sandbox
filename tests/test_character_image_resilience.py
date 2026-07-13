from app import export_html


def test_image_tag_has_local_fallback_and_alt_text():
    rendered = export_html._image_tag("https://example.test/a.png", "/fallback.svg", "ชื่อ")

    assert 'alt="ชื่อ"' in rendered
    assert 'loading="lazy"' in rendered
    assert "onerror" in rendered
    assert "/fallback.svg" in rendered


def test_missing_prompt_gets_deterministic_prompt():
    assert export_html._fallback_image_prompt("จักรพรรดิไรเซน") == "จักรพรรดิไรเซน character portrait"
