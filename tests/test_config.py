import os
from app import config
from app.llm_client import _gemini_response_schema
from app.schemas import SimulationBatchResult

def test_get_api_keys_skips_empty(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY_1", "aaa")
    monkeypatch.setenv("GROQ_API_KEY_2", "  ")
    monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert config.get_api_keys() == ["aaa"]


def test_get_api_keys_fallback_single(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY_1", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "single-key")
    assert config.get_api_keys() == ["single-key"]


def test_get_api_keys_comma_separated(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY_1", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "key-a,key-b, key-c")
    assert config.get_api_keys() == ["key-a", "key-b", "key-c"]


def test_get_openai_api_key_strips_whitespace(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "  test-openai-key  ")
    assert config.get_openai_api_key() == "test-openai-key"


def test_gemini_schema_omits_pydantic_default_values():
    """Gemini's Schema protobuf rejects Pydantic's JSON-Schema `default` field."""
    schema = _gemini_response_schema(SimulationBatchResult)

    def walk(value):
        if isinstance(value, dict):
            assert "default" not in value
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)
