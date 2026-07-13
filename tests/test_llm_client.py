from app import llm_client


def test_call_llm_uses_openai_after_groq_and_gemini_fail(monkeypatch):
    monkeypatch.setattr(llm_client.config, "get_api_keys", lambda: ["groq-key"])
    monkeypatch.setattr(llm_client.config, "get_gemini_api_keys", lambda: ["gemini-key"])
    monkeypatch.setattr(llm_client.config, "get_openai_api_key", lambda: "openai-key")
    monkeypatch.setattr(llm_client.random, "shuffle", lambda values: None)
    monkeypatch.setattr(
        llm_client, "_call_groq", lambda *args: (_ for _ in ()).throw(RuntimeError("groq"))
    )
    monkeypatch.setattr(
        llm_client, "_call_gemini", lambda *args: (_ for _ in ()).throw(RuntimeError("gemini"))
    )
    monkeypatch.setattr(llm_client, "_call_openai", lambda *args: '{"provider": "openai"}')
    monkeypatch.setattr(llm_client.time, "sleep", lambda _: None)

    assert llm_client.call_llm("prompt") == '{"provider": "openai"}'


def test_call_llm_does_not_try_openai_after_groq_success(monkeypatch):
    monkeypatch.setattr(llm_client.config, "get_api_keys", lambda: ["groq-key"])
    monkeypatch.setattr(llm_client.config, "get_gemini_api_keys", lambda: [])
    monkeypatch.setattr(llm_client.config, "get_openai_api_key", lambda: "openai-key")
    monkeypatch.setattr(llm_client.random, "shuffle", lambda values: None)
    monkeypatch.setattr(llm_client, "_call_groq", lambda *args: '{"provider": "groq"}')
    monkeypatch.setattr(
        llm_client,
        "_call_openai",
        lambda *args: (_ for _ in ()).throw(AssertionError("OpenAI must not run")),
    )

    assert llm_client.call_llm("prompt") == '{"provider": "groq"}'
