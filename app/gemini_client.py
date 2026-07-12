import time
import json
import re

from google import genai
from google.genai import types

from app import config

def clean_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)

current_key_index = 0


def get_current_key_display() -> int:
    return current_key_index + 1


def call_gemini(prompt: str, *, as_json: bool = False) -> str:
    global current_key_index
    keys = config.get_api_keys()
    if not keys:
        raise ValueError("No GEMINI_API_KEY_1/2/3 configured")
    last_err = None
    max_retries = 20  # เพิ่มเผื่อไว้ให้วนได้หลายรอบ
    base_sleep = 5
    consecutive_429 = 0
    
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=keys[current_key_index])
            kwargs = {"model": config.MODEL_NAME, "contents": prompt}
            if as_json:
                kwargs["config"] = types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            result = client.models.generate_content(**kwargs).text
            consecutive_429 = 0  # รีเซ็ตตัวนับถ้าสำเร็จ
            return result
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "401" in msg or "unauthenticated" in msg or "invalid authentication" in msg or "api key not valid" in msg:
                # ถ้าคีย์พังหรือโดนแบน (401/Invalid) ให้หมุนคีย์ทันที
                current_key_index = (current_key_index + 1) % len(keys)
                continue
            if "429" in msg or "too many requests" in msg or "quota" in msg:
                # [พลัง: การควบคุมเวลา (Time Manipulation)] 
                # หมุนกุญแจทันที ถ้าโดน 429
                current_key_index = (current_key_index + 1) % len(keys)
                consecutive_429 += 1
                
                # ถ้าโดน 429 ติดต่อกันจนครบรอบกุญแจ (เช่น 3 คีย์ ก็คือ 3 ครั้ง) ถึงจะเริ่ม Sleep
                if consecutive_429 % len(keys) == 0:
                    multiplier = consecutive_429 // len(keys)
                    sleep_time = base_sleep * (2 ** (multiplier - 1))
                    if sleep_time > 60:
                        sleep_time = 60
                    time.sleep(sleep_time)
                continue
            if "503" in msg or "unavailable" in msg or "overloaded" in msg:
                time.sleep(10)
                continue
            raise
            
    raise RuntimeError(f"API request failed after {max_retries} attempts. Last error: {last_err}")
