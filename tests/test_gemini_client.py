import app.gemini_client as gc


class FakeResp:
    def __init__(self, text):
        self.text = text


def test_rotates_on_429(monkeypatch):
    monkeypatch.setattr(gc.config, "get_api_keys", lambda: ["k1", "k2"])
    calls = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("429 Too Many Requests")
            return FakeResp("ok")

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = FakeModels()

    monkeypatch.setattr(gc.genai, "Client", FakeClient)
    gc.current_key_index = 0
    assert gc.call_gemini("hi") == "ok"
    assert gc.current_key_index == 1
