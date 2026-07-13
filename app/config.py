import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]  # project root
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "data" / "world.db"
CHRONICLE_DIR = ROOT / "chronicle"
MODEL_NAME = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()


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
            keys.extend(parts)
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
            keys.extend(parts)
    return keys


def get_openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def warn_if_no_keys() -> None:
    groq_keys = get_api_keys()
    gemini_keys = get_gemini_api_keys()
    openai_key = OPENAI_API_KEY
    if not groq_keys and not gemini_keys and not openai_key:
        print("[Config] WARNING: No LLM API keys configured. All LLM calls will fail.")


warn_if_no_keys()
