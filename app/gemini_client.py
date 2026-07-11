import time

from google import genai
from google.genai import types

from app import config

current_key_index = 0


def get_current_key_display() -> int:
    return current_key_index + 1


def call_gemini(prompt: str, *, as_json: bool = False) -> str:
    global current_key_index
    keys = config.get_api_keys()
    if not keys:
        raise ValueError("No GEMINI_API_KEY_1/2/3 configured")
    last_err = None
    for _ in range(len(keys)):
        try:
            client = genai.Client(api_key=keys[current_key_index])
            kwargs = {"model": config.MODEL_NAME, "contents": prompt}
            if as_json:
                kwargs["config"] = types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            return client.models.generate_content(**kwargs).text
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" in msg or "too many requests" in msg or "quota" in msg:
                current_key_index = (current_key_index + 1) % len(keys)
                time.sleep(1)
                continue
            raise
    raise RuntimeError(f"All API keys rate-limited: {last_err}")
