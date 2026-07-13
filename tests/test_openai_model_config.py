import importlib


def test_openai_model_defaults_to_supported_chat_model(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    from app import config

    importlib.reload(config)
    assert config.OPENAI_MODEL == "gpt-4o-mini"
