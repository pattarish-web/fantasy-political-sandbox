import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.world_reset import reset_world


def main():
    result = reset_world()
    print(result)


if __name__ == "__main__":
    main()
