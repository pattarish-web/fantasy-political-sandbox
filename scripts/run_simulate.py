import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import init_db
from app.simulation import run_simulation_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=1)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be at least 1")
    init_db()

    ok = 0

    for _ in range(args.rounds):
        result = run_simulation_batch(1)
        if result.get("error"):
            raise SystemExit(result["error"])
        ok += 1
        print("Batch completed: 1 event.")


if __name__ == "__main__":
    main()
