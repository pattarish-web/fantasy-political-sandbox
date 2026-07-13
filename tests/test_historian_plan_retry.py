import json

from app import historian


def test_request_plan_retries_invalid_structured_response(monkeypatch):
    responses = iter([
        {"source_rounds": [31, "32-ผิด"], "pov_characters": ["A"]},
        {"source_rounds": [31, 32], "pov_characters": ["A"], "central_conflict": "x", "political_stake": "y", "choice": "z", "cost": "c", "unresolved_thread": "u", "tone": "epic"},
    ])
    prompts = []

    monkeypatch.setattr(historian, "call_llm", lambda prompt, response_schema=None: prompts.append(prompt) or json.dumps(next(responses)))
    plan = historian._request_plan_with_retry("events", {}, "chars")

    assert plan.tone == "epic"
    assert len(prompts) == 2
    assert "tone" in prompts[1]
