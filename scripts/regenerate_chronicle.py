"""Regenerate every published chapter from the existing event log and canon rules."""

import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import config, db
from app.historian import run_historian


def regenerate() -> int:
    backup = Path(str(config.DB_PATH) + ".before-regenerate")
    if config.DB_PATH.exists():
        shutil.copy2(config.DB_PATH, backup)
        print(f"Backup created: {backup}")
        
    db.init_db()
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute("DELETE FROM chapters")
        conn.execute("DELETE FROM story_state")
        conn.commit()

    created = 0
    max_iterations = 100
    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        result = run_historian()
        if result.get("message") == "nothing to write":
            break
        if result.get("error"):
            raise RuntimeError(result["error"])
        created += 1
        print(f"[Regenerate] created chapter {created}: {result.get('title', '')}")
    if iteration >= max_iterations:
        print(f"[Regenerate] WARNING: Stopped after reaching {max_iterations} iterations to prevent infinite loop.")
    print(f"[Regenerate] completed {created} chapters; backup={backup}")
    return created


if __name__ == "__main__":
    regenerate()
