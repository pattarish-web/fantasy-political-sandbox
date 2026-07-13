import json
import sqlite3
from copy import deepcopy
from datetime import datetime, timezone

from app import config
from app.seed_data import INITIAL_CHARACTERS


DEFAULT_STORY_STATE = {
    "deaths": [],
    "regime_changes": [],
    "wars": [],
    "resolved_events": [],
    "open_threads": [],
    "character_changes": [],
    "relationship_changes": [],
    "artifacts": [],
    "faction_ledger": {},
}


def _connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def _ensure_appearances_and_metadata_column(cur) -> None:
    cur.execute("PRAGMA table_info(characters)")
    cols = {row[1] for row in cur.fetchall()}
    if "appearances" not in cols:
        cur.execute(
            "ALTER TABLE characters ADD COLUMN appearances INTEGER DEFAULT 0"
        )
    if "meta_data" not in cols:
        cur.execute(
            "ALTER TABLE characters ADD COLUMN meta_data TEXT DEFAULT '{}'"
        )


def init_db() -> None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                faction TEXT,
                personality TEXT,
                special_power TEXT,
                status TEXT DEFAULT 'Alive',
                appearances INTEGER DEFAULT 0,
                meta_data TEXT DEFAULT '{}'
            )
            """
        )
        _ensure_appearances_and_metadata_column(cur)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_num INTEGER,
                location TEXT,
                p1_name TEXT,
                p2_name TEXT,
                dialogue_text TEXT,
                consequence TEXT,
                is_drama INTEGER,
                story_facts TEXT DEFAULT '{}'
            )
            """
        )
        try:
            cur.execute("ALTER TABLE logs ADD COLUMN story_facts TEXT DEFAULT '{}'")
        except sqlite3.OperationalError:
            pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_num INTEGER UNIQUE,
                title TEXT,
                body TEXT,
                location TEXT,
                p1_name TEXT,
                p2_name TEXT,
                created_at TEXT,
                tone TEXT DEFAULT 'neutral'
            )
            """
        )
        # Attempt to add tone column to existing chapters table
        try:
            cur.execute("ALTER TABLE chapters ADD COLUMN tone TEXT DEFAULT 'neutral'")
        except sqlite3.OperationalError:
            pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS story_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state_json TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                owner_name TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                char1 TEXT,
                char2 TEXT,
                relationship_type TEXT,
                reason TEXT,
                UNIQUE(char1, char2)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aggressor_faction TEXT,
                defender_faction TEXT,
                reason TEXT,
                status TEXT DEFAULT 'Ongoing',
                UNIQUE(aggressor_faction, defender_faction)
            )
            """
        )
        _seed_initial_characters(cur)
        conn.commit()


def _seed_initial_characters(cur) -> None:
    for char in INITIAL_CHARACTERS:
        # char is now a tuple of length 6: (name, faction, personality, power, status, meta_data)
        cur.execute(
            """
            INSERT OR IGNORE INTO characters
            (name, faction, personality, special_power, status, appearances, meta_data)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            char,
        )


def reset_world_state() -> dict:
    with _connect() as conn:
        cur = conn.cursor()
        for table in ("logs", "chapters", "artifacts", "relationships", "wars", "story_state", "characters"):
            cur.execute(f"DELETE FROM {table}")
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('logs', 'chapters', 'artifacts', 'relationships', 'wars', 'characters')")
        except sqlite3.OperationalError:
            pass
        _seed_initial_characters(cur)
        conn.commit()

    return {
        "characters": len(INITIAL_CHARACTERS),
        "logs": 0,
        "chapters": 0,
        "artifacts": 0,
        "relationships": 0,
        "wars": 0,
    }


def _normalize_story_state(state: dict | None) -> dict:
    normalized = deepcopy(DEFAULT_STORY_STATE)
    if not isinstance(state, dict):
        return normalized
    for key, default_value in DEFAULT_STORY_STATE.items():
        value = state.get(key)
        if isinstance(value, type(default_value)):
            normalized[key] = deepcopy(value)
    return normalized


def get_story_state() -> dict:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT state_json FROM story_state WHERE id=1")
        row = cur.fetchone()
        if row:
            try:
                return _normalize_story_state(json.loads(row[0]))
            except (TypeError, json.JSONDecodeError):
                return _normalize_story_state(None)

        cur.execute("SELECT name FROM characters WHERE status='Dead' ORDER BY name")
        deaths = [record[0] for record in cur.fetchall()]
        cur.execute("SELECT round_num FROM chapters ORDER BY round_num")
        resolved_events = [f"round:{record[0]}" for record in cur.fetchall()]
        cur.execute(
            """
            SELECT aggressor_faction, defender_faction, reason
            FROM wars WHERE status='Ongoing'
            ORDER BY aggressor_faction, defender_faction
            """
        )
        wars = [
            {
                "aggressor_faction": record[0],
                "defender_faction": record[1],
                "reason": record[2],
            }
            for record in cur.fetchall()
        ]
        state = _normalize_story_state(
            {"deaths": deaths, "resolved_events": resolved_events, "wars": wars}
        )
        cur.execute(
            "INSERT INTO story_state (id, state_json) VALUES (1, ?)",
            (json.dumps(state, ensure_ascii=False),),
        )
        conn.commit()
        return state


def save_story_state(state: dict) -> None:
    serialized = json.dumps(_normalize_story_state(state), ensure_ascii=False)
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO story_state (id, state_json)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET state_json=excluded.state_json
            """,
            (serialized,),
        )
        conn.commit()


def get_alive_characters() -> list[tuple]:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, faction, personality, special_power, COALESCE(appearances, 0), meta_data
            FROM characters WHERE status='Alive'
            """
        )
        return cur.fetchall()

def get_dead_characters() -> list[str]:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM characters WHERE status='Dead'")
        return [row[0] for row in cur.fetchall()]


def get_character(name: str) -> dict | None:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, faction, personality, special_power, status, COALESCE(appearances, 0) as appearances, meta_data
            FROM characters WHERE name=?
            """,
            (name,)
        )
        row = cur.fetchone()
        if not row: return None
        return dict(row)


def parse_meta_data(meta_str: str | None) -> dict:
    import json
    if not meta_str:
        return {}
    try:
        return json.loads(meta_str)
    except:
        return {}


def _normalize_anime_prompt(prompt: str) -> str:
    cleaned = " ".join(str(prompt).split())
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if "anime" not in lowered:
        return f"anime style, japanese anime, {cleaned}"
    if "japanese" not in lowered:
        return f"japanese anime style, {cleaned}"
    return cleaned




def add_character_image_prompt(name: str, new_prompt: str, description: str = "") -> bool:
    import json
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT meta_data FROM characters WHERE name=?", (name,))
        row = cur.fetchone()
        if not row:
            return False

        meta = parse_meta_data(row[0])
        prompts = meta.get("image_prompts", [])

        old_prompt = meta.get("image_prompt")
        if old_prompt and not prompts:
            prompts.append({"prompt": _normalize_anime_prompt(old_prompt), "desc": "??????????? (Base Form)"})
            del meta["image_prompt"]

        entry = {"prompt": _normalize_anime_prompt(new_prompt), "desc": description or "????????????? (New Event)"}
        if prompts and prompts[-1].get("prompt") == entry["prompt"] and prompts[-1].get("desc") == entry["desc"]:
            return False
        prompts.append(entry)
        meta["image_prompts"] = prompts

        cur.execute("UPDATE characters SET meta_data=? WHERE name=?", (json.dumps(meta, ensure_ascii=False), name))
        conn.commit()
        return cur.rowcount > 0

def update_character_power(name: str, new_power: str) -> bool:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE characters SET special_power=? WHERE name=?", (new_power, name))
        conn.commit()
        return cur.rowcount > 0

def get_all_artifacts() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name, description, owner_name FROM artifacts ORDER BY name")
        return [dict(row) for row in cur.fetchall()]


def update_relationship(char1: str, char2: str, rel_type: str, reason: str = ""):
    # Always store alphabetically to prevent duplicates (A loves B == B loves A, etc)
    c1, c2 = sorted([char1, char2])
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO relationships (char1, char2, relationship_type, reason)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(char1, char2) DO UPDATE SET
                relationship_type = excluded.relationship_type,
                reason = excluded.reason
            """,
            (c1, c2, rel_type, reason)
        )
        conn.commit()


def declare_war(aggressor: str, defender: str, reason: str = ""):
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO wars (aggressor_faction, defender_faction, reason, status)
            VALUES (?, ?, ?, 'Ongoing')
            ON CONFLICT(aggressor_faction, defender_faction) DO UPDATE SET
                reason = excluded.reason,
                status = 'Ongoing'
            """,
            (aggressor, defender, reason)
        )
        conn.commit()


def get_all_relationships() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT char1, char2, relationship_type, reason FROM relationships")
        return [dict(row) for row in cur.fetchall()]


def get_active_wars() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT aggressor_faction, defender_faction, reason FROM wars WHERE status='Ongoing'")
        return [dict(row) for row in cur.fetchall()]

def insert_or_update_artifact(name: str, description: str, owner_name: str) -> None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM artifacts WHERE name=?", (name,))
        if cur.fetchone():
            cur.execute("UPDATE artifacts SET description=?, owner_name=? WHERE name=?", (description, owner_name, name))
        else:
            cur.execute("INSERT INTO artifacts (name, description, owner_name) VALUES (?, ?, ?)", (name, description, owner_name))
        conn.commit()

def transfer_artifact(artifact_name: str, new_owner_name: str) -> None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE artifacts SET owner_name=? WHERE name=?", (new_owner_name, artifact_name))
        conn.commit()

def get_artifacts_by_owner(owner_name: str) -> list[dict]:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description FROM artifacts WHERE owner_name=?", (owner_name,))
        return [
            {"id": row[0], "name": row[1], "description": row[2]}
            for row in cur.fetchall()
        ]


def count_alive() -> int:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM characters WHERE status='Alive'")
        return int(cur.fetchone()[0])


def list_character_names() -> list[str]:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM characters")
        return [row[0] for row in cur.fetchall()]


def insert_character(
    name: str,
    faction: str,
    personality: str,
    special_power: str,
    status: str = "Alive",
    meta_data: str = "{}"
) -> bool:
    """Insert a new character. Returns False if name already exists."""
    with _connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO characters
                (name, faction, personality, special_power, status, appearances, meta_data)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (name, faction, personality, special_power, status, meta_data),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def bump_appearances(*names: str) -> None:
    with _connect() as conn:
        cur = conn.cursor()
        for name in names:
            if not name:
                continue
            cur.execute(
                """
                UPDATE characters
                SET appearances = COALESCE(appearances, 0) + 1
                WHERE name = ?
                """,
                (name,),
            )
        conn.commit()


def get_character_spotlight(name: str) -> dict | None:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT faction, personality, special_power, appearances, meta_data
            FROM characters
            WHERE name = ?
            """,
            (name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def update_character_status(name: str, status: str) -> None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE characters SET status=? WHERE name=?", (status, name))
        conn.commit()


def save_log(
    round_num,
    location,
    p1_name,
    p2_name,
    dialogue,
    consequence,
    is_drama,
    story_facts: dict | None = None,
) -> None:
    serialized_facts = json.dumps(story_facts or {}, ensure_ascii=False)
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO logs
            (round_num, location, p1_name, p2_name, dialogue_text, consequence, is_drama, story_facts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (round_num, location, p1_name, p2_name, dialogue, consequence, is_drama, serialized_facts),
        )
        conn.commit()
    bump_appearances(p1_name, p2_name)


def get_latest_round() -> int:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MAX(round_num) FROM logs")
        res = cur.fetchone()[0]
        return res if res is not None else 0


def _decode_story_facts(raw_facts: str | None) -> dict:
    try:
        decoded = json.loads(raw_facts or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def get_undrafted_logs(limit: int) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT l.round_num, l.location, l.p1_name, l.p2_name,
                   l.dialogue_text, l.consequence, l.is_drama, l.story_facts
            FROM logs l
            WHERE l.round_num > (SELECT COALESCE(MAX(c.round_num), 0) FROM chapters c)
            ORDER BY l.round_num ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = [dict(row) for row in cur.fetchall()]
    for row in rows:
        row["story_facts"] = _decode_story_facts(row.get("story_facts"))
    return rows


def get_latest_undrafted_drama() -> tuple | None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT l.round_num, l.location, l.p1_name, l.p2_name, l.dialogue_text, l.consequence
            FROM logs l
            WHERE l.is_drama = 1
              AND l.round_num > (SELECT COALESCE(MAX(c.round_num), 0) FROM chapters c)
            ORDER BY l.round_num ASC
            LIMIT 1
            """
        )
        return cur.fetchone()


def save_chapter(
    round_num,
    title,
    body,
    location,
    p1_name,
    p2_name,
    tone='neutral',
    story_state: dict | None = None,
) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO chapters
            (round_num, title, body, location, p1_name, p2_name, created_at, tone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (round_num, title, body, location, p1_name, p2_name, created_at, tone),
        )
        if story_state is not None:
            cur.execute(
                """
                INSERT INTO story_state (id, state_json)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET state_json=excluded.state_json
                """,
                (json.dumps(_normalize_story_state(story_state), ensure_ascii=False),),
            )
        conn.commit()
        return cur.lastrowid


def list_chapters() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT round_num, title, body, location, p1_name, p2_name, created_at, tone
            FROM chapters
            ORDER BY round_num ASC
            """
        )
        return [dict(row) for row in cur.fetchall()]


def get_chapter_by_round(round_num: int) -> dict | None:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT round_num, title, body, location, p1_name, p2_name, created_at, tone
            FROM chapters
            WHERE round_num = ?
            """,
            (round_num,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_character_logs(name: str) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT round_num, location, p1_name, p2_name, dialogue_text, consequence, is_drama
            FROM logs
            WHERE p1_name = ? OR p2_name = ?
            ORDER BY round_num ASC
            """,
            (name, name),
        )
        return [dict(row) for row in cur.fetchall()]


def get_recent_global_logs(limit: int = 3) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT round_num, location, p1_name, p2_name, consequence
            FROM logs
            ORDER BY round_num DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_recent_global_logs_before(round_num: int, limit: int = 3) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT round_num, location, p1_name, p2_name, consequence
            FROM (
                SELECT round_num, location, p1_name, p2_name, consequence
                FROM logs
                WHERE round_num < ?
                ORDER BY round_num DESC
                LIMIT ?
            )
            ORDER BY round_num ASC
            """,
            (round_num, limit),
        )
        return [dict(row) for row in cur.fetchall()]


def list_all_characters() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, faction, personality, special_power, status, appearances, meta_data
            FROM characters
            ORDER BY name ASC
            """
        )
        return [dict(row) for row in cur.fetchall()]
