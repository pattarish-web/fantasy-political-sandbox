from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "world.db"
CHRONICLE_DIR = ROOT / "chronicle"
MODEL_NAME = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()

# Ollama Settings
USE_OLLAMA = os.environ.get("USE_OLLAMA", "false").lower() == "true"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

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
