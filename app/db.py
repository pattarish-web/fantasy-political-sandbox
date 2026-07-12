import sqlite3
from datetime import datetime, timezone

from app import config
from app.seed_data import INITIAL_CHARACTERS


def _connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(config.DB_PATH)


def _ensure_appearances_column(cur) -> None:
    cur.execute("PRAGMA table_info(characters)")
    cols = {row[1] for row in cur.fetchall()}
    if "appearances" not in cols:
        cur.execute(
            "ALTER TABLE characters ADD COLUMN appearances INTEGER DEFAULT 0"
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
                appearances INTEGER DEFAULT 0
            )
            """
        )
        _ensure_appearances_column(cur)
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
                is_drama INTEGER
            )
            """
        )
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
                created_at TEXT
            )
            """
        )
        for char in INITIAL_CHARACTERS:
            cur.execute(
                """
                INSERT OR IGNORE INTO characters
                (name, faction, personality, special_power, status, appearances)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                char,
            )
        conn.commit()


def get_alive_characters() -> list[tuple]:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, faction, personality, special_power, COALESCE(appearances, 0)
            FROM characters WHERE status='Alive'
            """
        )
        return cur.fetchall()


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
) -> bool:
    """Insert a new character. Returns False if name already exists."""
    with _connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO characters
                (name, faction, personality, special_power, status, appearances)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (name, faction, personality, special_power, status),
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
            SELECT name, faction, personality, special_power, status,
                   COALESCE(appearances, 0) AS appearances
            FROM characters WHERE name = ?
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
) -> None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO logs
            (round_num, location, p1_name, p2_name, dialogue_text, consequence, is_drama)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (round_num, location, p1_name, p2_name, dialogue, consequence, is_drama),
        )
        conn.commit()
    bump_appearances(p1_name, p2_name)


def get_latest_round() -> int:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MAX(round_num) FROM logs")
        res = cur.fetchone()[0]
        return res if res is not None else 0


def get_latest_undrafted_drama() -> tuple | None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT l.round_num, l.location, l.p1_name, l.p2_name, l.dialogue_text, l.consequence
            FROM logs l
            WHERE l.is_drama = 1
              AND NOT EXISTS (SELECT 1 FROM chapters c WHERE c.round_num = l.round_num)
            ORDER BY l.round_num DESC
            LIMIT 1
            """
        )
        return cur.fetchone()


def save_chapter(round_num, title, body, location, p1_name, p2_name) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO chapters
            (round_num, title, body, location, p1_name, p2_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (round_num, title, body, location, p1_name, p2_name, created_at),
        )
        conn.commit()
        return cur.lastrowid


def list_chapters() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT round_num, title, body, location, p1_name, p2_name, created_at
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
            SELECT round_num, title, body, location, p1_name, p2_name, created_at
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


def list_all_characters() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, faction, personality, special_power, status, COALESCE(appearances, 0) AS appearances
            FROM characters
            ORDER BY name ASC
            """
        )
        return [dict(row) for row in cur.fetchall()]
