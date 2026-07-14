"""One-time migration for the reboot cast's political stances."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db
from app.seed_data_new import stance_for_faction


def update() -> int:
    db.init_db()
    changed = 0
    with db._connect() as conn:
        rows = conn.execute("SELECT name, faction, meta_data FROM characters").fetchall()
        for name, faction, raw_meta in rows:
            meta = db.parse_meta_data(raw_meta)
            meta["morality"] = stance_for_faction(faction, meta.get("morality"))
            conn.execute("UPDATE characters SET meta_data=? WHERE name=?", (json.dumps(meta, ensure_ascii=False), name))
            changed += 1
        conn.commit()
    print(f"updated {changed} character stances")
    return changed


if __name__ == "__main__":
    update()
