import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import init_db
from app.historian import run_historian


def main():
    init_db()
    result = run_historian()
    if result.get("error"):
        raise SystemExit(result["error"])
    print(result)


if __name__ == "__main__":
    main()
