from app import historian


def test_unsupported_tone_is_normalized_without_changing_plan_content():
    plan = historian.ChapterPlan(
        source_rounds=[1], pov_characters=["A"], central_conflict="conflict",
        political_stake="stake", choice="choice", cost="cost",
        unresolved_thread="thread", tone="political",
    )

    normalized = historian._normalize_plan_tone(plan)

    assert normalized.tone == "neutral"
    assert normalized.central_conflict == "conflict"
    assert normalized.source_rounds == [1]
