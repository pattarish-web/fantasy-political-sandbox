"""Regenerate every published chapter from the existing event log and canon rules."""

import os
import shutil
import sqlite3
from pathlib import Path

from app import config, db
from app.historian import run_historian


def regenerate() -> int:
    db.init_db()
    backup = Path(str(config.DB_PATH) + ".before-regenerate")
    shutil.copy2(config.DB_PATH, backup)
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute("DELETE FROM chapters")
        conn.execute("DELETE FROM story_state")
        conn.commit()

    created = 0
    while True:
        result = run_historian()
        if result.get("message") == "nothing to write":
            break
        if result.get("error"):
            raise RuntimeError(result["error"])
        created += 1
        print(f"[Regenerate] created chapter {created}: {result.get('title', '')}")
    print(f"[Regenerate] completed {created} chapters; backup={backup}")
    return created


if __name__ == "__main__":
    regenerate()
