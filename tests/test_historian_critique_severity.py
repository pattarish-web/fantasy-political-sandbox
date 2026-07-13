from app import historian


def test_critique_severity_blocks_canon_and_allows_style_warning():
    assert historian._critique_is_blocking(["ตัวละครขัดกับ canon และเหตุการณ์ไม่ต่อเนื่อง"])
    assert not historian._critique_is_blocking(["บทพูดซ้ำและน้ำเสียงยังไม่คม"])
