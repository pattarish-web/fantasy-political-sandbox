import os
from app import config

def test_get_api_keys_skips_empty(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1", "aaa")
    monkeypatch.setenv("GEMINI_API_KEY_2", "  ")
    monkeypatch.delenv("GEMINI_API_KEY_3", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert config.get_api_keys() == ["aaa"]


def test_get_api_keys_fallback_single(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY_1", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_3", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "single-key")
    assert config.get_api_keys() == ["single-key"]
