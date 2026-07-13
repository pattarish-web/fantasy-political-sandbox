from app import export_html


def test_resilient_image_tag_is_clickable_for_lightbox():
    rendered = export_html._image_tag("https://example.test/a.png", "placeholder.svg", "ภาพ")

    assert 'onclick="openLightbox(this.src)"' in rendered
