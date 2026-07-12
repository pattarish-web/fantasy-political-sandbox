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
    init_db()
    
    rounds_left = args.rounds
    ok = 0
    
    while rounds_left > 0:
        batch_size = min(5, rounds_left)
        result = run_simulation_batch(batch_size)
        if result.get("error"):
            raise SystemExit(result["error"])
        ok += batch_size
        rounds_left -= batch_size
        print(f"Batch completed: {batch_size} events.")

    if ok == 0:
        raise SystemExit("no rounds completed")


if __name__ == "__main__":
    main()
