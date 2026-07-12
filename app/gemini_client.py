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
    max_retries = 10  # [พลัง: ความทนทานเหนือมนุษย์] เพิ่มจำนวนครั้งที่ลองใหม่ให้สูงขึ้น
    base_sleep = 5
    
    for attempt in range(max_retries):
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
            if "401" in msg or "unauthenticated" in msg or "invalid authentication" in msg:
                raise ValueError(
                    "Gemini API key ไม่ถูกต้อง (401) — ตรวจค่า GEMINI_API_KEY ใน GitHub Secrets "
                    "ว่าเป็น API key จาก AI Studio ไม่มีช่องว่าง/ขึ้นบรรทัดใหม่"
                ) from e
            if "429" in msg or "too many requests" in msg or "quota" in msg:
                # [พลัง: การควบคุมเวลา (Time Manipulation)] 
                # หมุนกุญแจ (Key Rotation) + สลับกุญแจแล้วหน่วงเวลาแบบ Exponential Backoff
                current_key_index = (current_key_index + 1) % len(keys)
                sleep_time = base_sleep * (2 ** attempt)  # 5s, 10s, 20s, 40s...
                # จำกัดการรอสูงสุดไม่เกิน 60 วินาทีต่อรอบ
                if sleep_time > 60:
                    sleep_time = 60
                time.sleep(sleep_time)
                continue
            if "503" in msg or "unavailable" in msg or "overloaded" in msg:
                time.sleep(10)
                continue
            raise
            
    raise RuntimeError(f"API request failed after {max_retries} attempts. Last error: {last_err}")
