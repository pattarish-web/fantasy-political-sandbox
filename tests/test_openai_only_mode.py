import json

from app import llm_client


def test_call_llm_openai_only_skips_other_providers(monkeypatch):
    calls = []
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setattr(llm_client.config, "get_openai_api_key", lambda: "key")
    monkeypatch.setattr(llm_client, "_call_openai", lambda prompt, key, schema=None: calls.append("openai") or json.dumps({"ok": True}))
    monkeypatch.setattr(llm_client, "_call_groq", lambda *args: calls.append("groq"))
    monkeypatch.setattr(llm_client, "_call_gemini", lambda *args: calls.append("gemini"))

    assert json.loads(llm_client.call_llm("test"))["ok"] is True
    assert calls == ["openai"]
