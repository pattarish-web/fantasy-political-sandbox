import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import init_db
from app.simulation import run_simulation_round


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=1)
    args = parser.parse_args()
    init_db()
    ok = 0
    for _ in range(args.rounds):
        result = run_simulation_round()
        if result.get("error"):
            raise SystemExit(result["error"])
        ok += 1
        print(result)
    if ok == 0:
        raise SystemExit("no rounds completed")


if __name__ == "__main__":
    main()
