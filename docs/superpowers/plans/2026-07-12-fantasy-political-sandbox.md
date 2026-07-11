# Fantasy Political Sandbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a hosted Flask app with a mobile-first dashboard (simulate 1/10, historian, chronicle reading) backed by SQLite and Gemini keys with 429 rotation.

**Architecture:** Python package `app/` holds DB, Gemini client, simulation, historian, and HTML export. Flask serves one responsive dashboard plus chronicle pages and JSON APIs. Optional CLI scripts and GitHub Actions mirror the same logic for backup runs. Persist `data/world.db` on a host volume.

**Tech Stack:** Python 3.11+, Flask, gunicorn, google-genai, python-dotenv, pytest, SQLite

## Global Constraints

- Never commit real API keys or `.env` with secrets.
- Env keys: `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3` (skip empty).
- On 429 / quota / too many requests: rotate key and retry; fail if all keys exhausted.
- Model default: `gemini-2.5-flash`.
- UI primary target: phone browser; same buttons as PC prototype.
- No coupling to `sangkan-clean` or cleaning-seo-website.
- Spec: `docs/superpowers/specs/2026-07-12-fantasy-political-sandbox-design.md`

## File map

| Path | Responsibility |
|------|----------------|
| `app/config.py` | Paths, model name, load API keys from env |
| `app/db.py` | SQLite schema, seed, CRUD |
| `app/seed_data.py` | INITIAL_CHARACTERS, LOCATIONS |
| `app/gemini_client.py` | `call_gemini(prompt, *, as_json) -> str` with rotation |
| `app/simulation.py` | `run_simulation_round() -> dict` |
| `app/historian.py` | `run_historian() -> dict` |
| `app/export_html.py` | Write/update `chronicle/*.html` |
| `app/routes.py` | Flask blueprints/routes |
| `app/__init__.py` | `create_app()` |
| `templates/mobile_dashboard.html` | Controls + log |
| `templates/chronicle_index.html` | Chapter list |
| `templates/chronicle_chapter.html` | One chapter |
| `static/app.css` | Mobile-first styles |
| `scripts/run_simulate.py` | CLI `--rounds N` |
| `scripts/run_historian.py` | CLI historian |
| `tests/` | pytest suite |
| `requirements.txt`, `Procfile`, `render.yaml`, `README.md`, `.gitignore` | deps + deploy |

---

### Task 1: Scaffold + config + seed data

**Files:**
- Create: `requirements.txt`, `.gitignore`, `app/__init__.py`, `app/config.py`, `app/seed_data.py`, `tests/test_config.py`, `pytest.ini`
- Create: `data/.gitkeep`, `chronicle/.gitkeep`

**Interfaces:**
- Produces: `app.config.get_api_keys() -> list[str]`, `MODEL_NAME: str`, `DB_PATH: Path`, `ROOT: Path`
- Produces: `app.seed_data.INITIAL_CHARACTERS: list[tuple]`, `LOCATIONS: list[str]`

- [ ] **Step 1: Write failing test for key loading**

```python
# tests/test_config.py
import os
from app import config

def test_get_api_keys_skips_empty(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_1", "aaa")
    monkeypatch.setenv("GEMINI_API_KEY_2", "  ")
    monkeypatch.delenv("GEMINI_API_KEY_3", raising=False)
    assert config.get_api_keys() == ["aaa"]
```

- [ ] **Step 2: Run test — expect fail (module missing)**

Run: `pytest tests/test_config.py::test_get_api_keys_skips_empty -v`  
Expected: FAIL import error

- [ ] **Step 3: Implement scaffold**

`requirements.txt`:
```
flask>=3.0
gunicorn>=22.0
google-genai>=1.0
python-dotenv>=1.0
pytest>=8.0
```

`.gitignore`:
```
.env
__pycache__/
*.pyc
.venv/
venv/
data/*.db
.pytest_cache/
```

`pytest.ini`:
```
[pytest]
pythonpath = .
testpaths = tests
```

`app/config.py`:
```python
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "world.db"
CHRONICLE_DIR = ROOT / "chronicle"
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()

def get_api_keys() -> list[str]:
    keys = []
    for i in (1, 2, 3):
        k = os.environ.get(f"GEMINI_API_KEY_{i}", "")
        if k and k.strip():
            keys.append(k.strip())
    return keys
```

`app/seed_data.py`: copy `INITIAL_CHARACTERS` (20 tuples) and `LOCATIONS` exactly from the user prototype.

`app/__init__.py`:
```python
def create_app():
    from flask import Flask
    from app.db import init_db
    from app import routes

    app = Flask(__name__, template_folder=str((__import__("pathlib").Path(__file__).parent.parent / "templates")),
                static_folder=str((__import__("pathlib").Path(__file__).parent.parent / "static")))
    init_db()
    app.register_blueprint(routes.bp)
    return app
```
( defer full `create_app` wiring until Task 6 if routes missing — for Task 1 only create empty `app/__init__.py` with docstring and implement `create_app` in Task 6. For Task 1 use:)

```python
# app/__init__.py
"""Fantasy political sandbox application package."""
```

- [ ] **Step 4: Run test — expect pass**

Run: `python -m venv .venv` then activate; `pip install -r requirements.txt`; `pytest tests/test_config.py::test_get_api_keys_skips_empty -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore pytest.ini app/config.py app/seed_data.py app/__init__.py tests/test_config.py data/.gitkeep chronicle/.gitkeep
git commit -m "chore: scaffold config, seed data, and pytest"
```

---

### Task 2: Database layer

**Files:**
- Create: `app/db.py`, `tests/test_db.py`

**Interfaces:**
- Consumes: `config.DB_PATH`, `seed_data.INITIAL_CHARACTERS`
- Produces:
  - `init_db() -> None`
  - `get_alive_characters() -> list[tuple]`
  - `update_character_status(name: str, status: str) -> None`
  - `save_log(round_num, location, p1_name, p2_name, dialogue, consequence, is_drama) -> None`
  - `get_latest_round() -> int`
  - `get_latest_undrafted_drama() -> tuple | None`  
    `(round_num, location, p1_name, p2_name, dialogue_text, consequence)`
  - `save_chapter(round_num, title, body, location, p1_name, p2_name) -> int`
  - `list_chapters() -> list[dict]`
  - `get_chapter_by_round(round_num: int) -> dict | None`
  - `count_alive() -> int`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_db.py
from pathlib import Path
import app.config as config
from app import db

def test_init_seeds_characters(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    alive = db.get_alive_characters()
    assert len(alive) == 20

def test_save_log_and_latest_round(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    db.save_log(1, "วิหาร", "A", "B", "hi", "ok", 1)
    assert db.get_latest_round() == 1

def test_undrafted_drama_and_chapter(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    db.save_log(2, "สภา", "A", "B", "d", "c", 1)
    row = db.get_latest_undrafted_drama()
    assert row[0] == 2
    db.save_chapter(2, "ชื่อตอน", "เนื้อเรื่อง", "สภา", "A", "B")
    assert db.get_latest_undrafted_drama() is None
    assert db.get_chapter_by_round(2)["title"] == "ชื่อตอน"
```

- [ ] **Step 2: Run tests — expect fail**

Run: `pytest tests/test_db.py -v`  
Expected: FAIL import/attribute

- [ ] **Step 3: Implement `app/db.py`**

Use `sqlite3`, `CREATE TABLE IF NOT EXISTS` for `characters`, `logs`, `chapters` per spec. Seed with `INSERT OR IGNORE`. `get_latest_undrafted_drama` = drama logs ordered by `round_num DESC` where `round_num` not in `chapters`.

```python
def get_latest_undrafted_drama():
    with sqlite3.connect(config.DB_PATH) as conn:
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
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/test_db.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: add SQLite schema, seed, and chapter helpers"
```

---

### Task 3: Gemini client with key rotation

**Files:**
- Create: `app/gemini_client.py`, `tests/test_gemini_client.py`

**Interfaces:**
- Consumes: `config.get_api_keys()`, `config.MODEL_NAME`
- Produces: `call_gemini(prompt: str, *, as_json: bool = False) -> str`  
  Module-level `current_key_index: int` for status display  
  Produces: `get_current_key_display() -> int` (1-based)

- [ ] **Step 1: Write failing tests with fake client**

```python
# tests/test_gemini_client.py
import app.gemini_client as gc

class FakeResp:
    def __init__(self, text):
        self.text = text

def test_rotates_on_429(monkeypatch):
    monkeypatch.setattr(gc.config, "get_api_keys", lambda: ["k1", "k2"])
    calls = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("429 Too Many Requests")
            return FakeResp("ok")

    class FakeClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = FakeModels()

    monkeypatch.setattr(gc.genai, "Client", FakeClient)
    gc.current_key_index = 0
    assert gc.call_gemini("hi") == "ok"
    assert gc.current_key_index == 1
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/test_gemini_client.py::test_rotates_on_429 -v`

- [ ] **Step 3: Implement `app/gemini_client.py`**

```python
import time
from google import genai
from google.genai import types
from app import config

current_key_index = 0

def get_current_key_display() -> int:
    return current_key_index + 1

def call_gemini(prompt: str, *, as_json: bool = False) -> str:
    global current_key_index
    keys = config.get_api_keys()
    if not keys:
        raise ValueError("No GEMINI_API_KEY_1/2/3 configured")
    last_err = None
    for _ in range(len(keys)):
        try:
            client = genai.Client(api_key=keys[current_key_index])
            kwargs = {"model": config.MODEL_NAME, "contents": prompt}
            if as_json:
                kwargs["config"] = types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            return client.models.generate_content(**kwargs).text
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" in msg or "too many requests" in msg or "quota" in msg:
                current_key_index = (current_key_index + 1) % len(keys)
                time.sleep(1)
                continue
            raise
    raise RuntimeError(f"All API keys rate-limited: {last_err}")
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_gemini_client.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/gemini_client.py tests/test_gemini_client.py
git commit -m "feat: Gemini client with 429 key rotation"
```

---

### Task 4: Simulation round

**Files:**
- Create: `app/simulation.py`, `tests/test_simulation.py`

**Interfaces:**
- Consumes: `db.*`, `seed_data.LOCATIONS`, `gemini_client.call_gemini`
- Produces: `run_simulation_round(round_number: int | None = None) -> dict`  
  Success keys: `round_num`, `location`, `chars`, `dialogue`, `consequence`, `is_drama`, optional `death_notice`  
  Error: `{"error": str}`

- [ ] **Step 1: Write failing test with mocked Gemini**

```python
# tests/test_simulation.py
import json
from app import config, db, simulation

def test_run_simulation_round_saves_log(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    payload = {
        "dialogue": "a: hi\nb: bye",
        "consequence": "nothing",
        "is_drama": 0,
        "character_killed": None,
    }
    monkeypatch.setattr(
        simulation,
        "call_gemini",
        lambda prompt, as_json=False: json.dumps(payload),
    )
    result = simulation.run_simulation_round()
    assert "error" not in result
    assert result["round_num"] == 1
    assert db.get_latest_round() == 1
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement `app/simulation.py`**

Port prototype prompt (Thai dialogue JSON). Use `clean_json_response` (strip \`\`\` fences then `json.loads`). Random two alive chars + location. On kill, `update_character_status`. Import `call_gemini` from `app.gemini_client`.

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_simulation.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/simulation.py tests/test_simulation.py
git commit -m "feat: simulation round engine"
```

---

### Task 5: Historian + HTML export

**Files:**
- Create: `app/historian.py`, `app/export_html.py`, `tests/test_historian.py`, `tests/test_export_html.py`

**Interfaces:**
- Produces: `run_historian() -> dict` with `novel`/`title`/`round_num` or `error`/`message`
- Produces: `export_chapter(chapter: dict) -> Path`, `rebuild_index(chapters: list[dict]) -> Path`  
  Files: `chronicle/chapter-{round:03d}.html`, `chronicle/index.html`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_historian.py
import json
from app import config, db, historian

def test_historian_writes_chapter(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path / "chronicle")
    config.CHRONICLE_DIR.mkdir()
    db.init_db()
    db.save_log(3, "สลัม", "A", "B", "d", "c", 1)
    monkeypatch.setattr(
        historian,
        "call_gemini",
        lambda prompt, as_json=False: json.dumps(
            {"title": "บททดสอบ", "body": "เนื้อหา"}
        ),
    )
    result = historian.run_historian()
    assert result["title"] == "บททดสอบ"
    assert db.get_chapter_by_round(3) is not None
    assert (config.CHRONICLE_DIR / "chapter-003.html").exists()
```

```python
# tests/test_export_html.py
from app import export_html
from pathlib import Path

def test_export_contains_viewport(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "CHRONICLE_DIR", tmp_path)
    path = export_html.export_chapter({
        "round_num": 1,
        "title": "ท",
        "body": "ย่อหน้าหนึ่ง\n\nย่อหน้าสอง",
        "location": "สภา",
        "p1_name": "A",
        "p2_name": "B",
    })
    html = path.read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert "ท" in html
```

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement historian + export**

Historian: load undrafted drama; if none return `{"message": "nothing to write"}` (exit OK for CLI later). Prompt asks JSON title+body; include character statuses from DB. Call `save_chapter` then `export_chapter` + `rebuild_index(list_chapters())`.

Export HTML: mobile CSS inline or linked `/static/app.css`; escape user content with `html.escape`; convert body newlines to `<p>`.

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_historian.py tests/test_export_html.py -v`

- [ ] **Step 5: Commit**

```bash
git add app/historian.py app/export_html.py tests/test_historian.py tests/test_export_html.py
git commit -m "feat: historian and mobile chronicle HTML export"
```

---

### Task 6: Flask routes + mobile UI

**Files:**
- Create: `app/routes.py`, `templates/mobile_dashboard.html`, `templates/chronicle_index.html`, `templates/chronicle_chapter.html`, `static/app.css`, `run.py`, `tests/test_routes.py`
- Modify: `app/__init__.py` → implement `create_app()`

**Interfaces:**
- Routes:
  - `GET /` dashboard
  - `GET /chronicle` index
  - `GET /chronicle/<int:round_num>` chapter
  - `GET /api/status` → `{alive, round, current_api_index}`
  - `POST /api/simulate` body optional JSON `{times: 1}` — for times>1 loop server-side or client loops `GET`-style single round; **use `POST /api/simulate` once per round** (client loops 10) matching prototype
  - `POST /api/historian`
- Optional: if `APP_PASSWORD` set, require header `X-App-Password` or form password for mutating routes

- [ ] **Step 1: Write failing route tests**

```python
# tests/test_routes.py
from app import config, db
from app import create_app

def test_status_and_simulate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "APP_PASSWORD", "")
    import json
    from app import simulation
    monkeypatch.setattr(
        simulation,
        "run_simulation_round",
        lambda: {"round_num": 1, "location": "x", "chars": "a VS b",
                 "dialogue": "d", "consequence": "c", "is_drama": 0},
    )
    app = create_app()
    client = app.test_client()
    s = client.get("/api/status").get_json()
    assert "alive" in s
    r = client.post("/api/simulate")
    assert r.status_code == 200
    assert r.get_json()["round_num"] == 1
```

Note: `create_app` must call `init_db()` so status works.

- [ ] **Step 2: Run — expect fail**

- [ ] **Step 3: Implement UI + routes**

Dashboard HTML (Thai labels matching prototype):
- Status: รอบล่าสุด / ตัวละครที่มีชีวิต / API ปัจจุบัน
- Buttons: รันจำลอง 1 รอบ, รันจำลอง 10 รอบ, อาลักษณ์หลวง, ลิงก์พงศาวดาร
- Log window
- JS: `fetch('/api/simulate', {method:'POST'})` in loop for 10; disable buttons while loading
- CSS: min 18px, large tap targets (min-height 48px), dark theme ok if readable; viewport meta

`run.py`:
```python
from app import create_app
app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/test_routes.py -v`  
Manual: `python run.py` → open phone to LAN IP or browser

- [ ] **Step 5: Commit**

```bash
git add app/__init__.py app/routes.py templates static run.py tests/test_routes.py
git commit -m "feat: mobile Flask dashboard and API routes"
```

---

### Task 7: CLI scripts + deploy docs

**Files:**
- Create: `scripts/run_simulate.py`, `scripts/run_historian.py`, `Procfile`, `render.yaml`, `README.md`, `.env.example`

**Interfaces:**
- CLI exits 0 on success or historian “nothing to write”
- `Procfile`: `web: gunicorn "app:create_app()" -b 0.0.0.0:$PORT`

- [ ] **Step 1: Implement CLIs**

```python
# scripts/run_simulate.py
import argparse
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
```

```python
# scripts/run_historian.py
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
```

`.env.example`:
```
GEMINI_API_KEY_1=
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=
GEMINI_MODEL=gemini-2.5-flash
APP_PASSWORD=
```

`README.md` sections: what it is; local run; env vars; deploy on Render (persistent disk mount at `data/`); optional password; optional Actions later.

`render.yaml` sketch: web service, disk `data`, env groups for the three keys.

- [ ] **Step 2: Smoke CLI without keys**

Run: `python scripts/run_simulate.py --rounds 1`  
Expected: exit non-zero with clear “No GEMINI_API_KEY…” or similar

- [ ] **Step 3: Commit**

```bash
git add scripts Procfile render.yaml README.md .env.example
git commit -m "docs: add CLI, deploy config, and README"
```

---

### Task 8: Optional GitHub Actions backup

**Files:**
- Create: `.github/workflows/simulate.yml`, `.github/workflows/historian.yml`

- [ ] **Step 1: Add workflows**

`simulate.yml`: `workflow_dispatch` input `rounds` (1–50); checkout; setup-python 3.11; pip install; run script with secrets mapped to env; commit `data/world.db` if changed (using `git config` bot identity in workflow only).

`historian.yml`: same pattern; commit `data/world.db` + `chronicle/`.

Note: committing DB from Actions is optional backup; hosted app remains primary. If repo `data/*.db` is gitignored, adjust `.gitignore` to allow `data/world.db` **or** force-add in workflow. **Decision for implementer:** change `.gitignore` to ignore only local overrides, track `data/world.db` when present for Actions continuity — use:

```
data/*.db
!data/world.db
```

only if adopting Actions sync; otherwise keep DB local-only on host disk and skip committing DB from Actions (artifact upload instead). **Prefer for v1:** Actions upload artifacts; do not fight gitignore — simpler.

Prefer v1 Actions: upload `world.db` + chronicle as artifacts (no commit). Document that phone UX uses the hosted app.

- [ ] **Step 2: Commit workflows**

```bash
git add .github/workflows
git commit -m "ci: optional simulate/historian workflows with artifacts"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Hosted Flask + mobile buttons like PC | Task 6 |
| Key rotation 429 | Task 3 |
| SQLite characters/logs/chapters | Task 2 |
| Simulate + historian | Tasks 4–5 |
| Mobile chronicle HTML | Task 5–6 |
| Persistent disk / deploy docs | Task 7 |
| Optional Actions | Task 8 |
| No keys in git | `.gitignore` + `.env.example` Task 1/7 |
| APP_PASSWORD optional | Task 6–7 |

No TBD placeholders remain. Interface names are consistent (`call_gemini`, `run_simulation_round`, `run_historian`, `create_app`).

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-12-fantasy-political-sandbox.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
