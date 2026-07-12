import os
from app import config

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
