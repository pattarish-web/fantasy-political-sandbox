from app import simulation


def test_validated_encounters_retries_after_invalid_ai_payload(monkeypatch):
    responses = iter([
        {"encounters": [{"p1_name": "A", "p2_name": "Ghost"}]},
        {"encounters": [{"p1_name": "A", "p2_name": "B", "dialogue": "ตกลง", "consequence": "เกิดพันธมิตร"}]},
    ])

    result = simulation._validated_encounters(
        lambda _feedback: next(responses),
        batch_size=1,
        alive_names={"A", "B"},
    )

    assert result["error"] is None
    assert result["attempts"] == 2
    assert result["encounters"][0]["p2_name"] == "B"


def test_validated_encounters_stops_after_two_retries(monkeypatch):
    result = simulation._validated_encounters(
        lambda _feedback: {"encounters": [{"p1_name": "A", "p2_name": "Ghost"}]},
        batch_size=1,
        alive_names={"A", "B"},
    )

    assert result["error"] == "Encounter participants must be distinct known living characters"
    assert result["attempts"] == 3
