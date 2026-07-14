import pytest
from app import llm_client


def test_call_llm_uses_openai_only(monkeypatch):
    monkeypatch.setattr(llm_client.config, "get_openai_api_key", lambda: "openai-key")
    monkeypatch.setattr(llm_client, "_call_openai", lambda *args: '{"provider": "openai"}')

    assert llm_client.call_llm("prompt") == '{"provider": "openai"}'


def test_call_llm_raises_without_openai_key(monkeypatch):
    monkeypatch.setattr(llm_client.config, "get_openai_api_key", lambda: "")
    
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is unavailable"):
        llm_client.call_llm("prompt")

