from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "world.db"
CHRONICLE_DIR = ROOT / "chronicle"
MODEL_NAME = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()



def get_api_keys() -> list[str]:
    keys = []
    for i in (1, 2, 3):
        k = os.environ.get(f"GROQ_API_KEY_{i}", "")
        if k and k.strip():
            keys.append(k.strip())
    if not keys:
        k = os.environ.get("GROQ_API_KEY", "")
        if k and k.strip():
            parts = [p.strip() for p in k.split(",") if p.strip()]
            keys.extend(parts if len(parts) > 1 else [k.strip()])
    return keys

def get_gemini_api_keys() -> list[str]:
    keys = []
    for i in (1, 2, 3):
        k = os.environ.get(f"GEMINI_API_KEY_{i}", "")
        if k and k.strip():
            keys.append(k.strip())
    if not keys:
        k = os.environ.get("GEMINI_API_KEY", "")
        if k and k.strip():
            parts = [p.strip() for p in k.split(",") if p.strip()]
            keys.extend(parts if len(parts) > 1 else [k.strip()])
    return keys


def get_openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()
