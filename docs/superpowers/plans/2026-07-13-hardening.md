# Fantasy Political Sandbox Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reliably publish automated chronicles while rejecting unsafe requests and invalid simulation state.

**Architecture:** Add pure batch validation before SQLite writes, gate mutating routes centrally, and serialize state-writing workflows.

**Tech Stack:** Python 3.11, Flask, pytest, SQLite, GitHub Actions.

## Global Constraints

- Preserve the existing SQLite schema and public read-only routes.
- Keep Groq as primary LLM and Gemini as fallback.
- Never write a partial batch when validation fails.
- Every state-writing workflow uses `group: world-state` and `cancel-in-progress: false`.

---

### Task 1: Validate simulation batches before persistence

**Files:**
- Modify: `app/simulation.py`
- Replace: `tests/test_simulation.py`

**Interfaces:**
- Produces: `validate_encounters(encounters: list[dict], alive_names: set[str], locations: set[str]) -> str | None`.

- [ ] **Step 1: Write failing tests**

```python
def test_batch_rejects_unknown_participant_without_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    known = db.get_alive_characters()[0][0]
    monkeypatch.setattr(simulation, "call_llm", lambda *_a, **_k: json.dumps({
        "encounters": [{"p1_name": "Unknown", "p2_name": known,
        "location": simulation.LOCATIONS[0], "dialogue": "x",
        "consequence": "x", "is_drama": 0}]}))
    result = simulation.run_simulation_batch(1)
    assert result["error"] == "unknown participant: Unknown"
    assert db.get_latest_round() == 0

def test_validator_rejects_character_killed_before_later_encounter():
    events = [
        {"p1_name": "A", "p2_name": "B", "location": "L", "character_killed": "A"},
        {"p1_name": "A", "p2_name": "C", "location": "L"},
    ]
    assert simulation.validate_encounters(events, {"A", "B", "C"}, {"L"}) == "dead participant: A"
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_simulation.py -v`

Expected: FAIL because no validator exists and invalid model output is persisted.

- [ ] **Step 3: Implement minimal validation**

```python
def validate_encounters(encounters, alive_names, locations):
    alive = set(alive_names)
    for encounter in encounters:
        p1, p2 = encounter.get("p1_name"), encounter.get("p2_name")
        for name in (p1, p2):
            if name not in alive_names:
                return f"unknown participant: {name}"
            if name not in alive:
                return f"dead participant: {name}"
        if p1 == p2:
            return "participants must be different"
        if encounter.get("location") not in locations:
            return f"unknown location: {encounter.get('location')}"
        killed = encounter.get("character_killed")
        if killed and killed not in {p1, p2}:
            return f"killed character is not a participant: {killed}"
        if killed:
            alive.remove(killed)
    return None
```

Call it immediately after the encounter-count check and before the `db.save_log` loop. On error, return `{"error": error, "born": born}`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_simulation.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/simulation.py tests/test_simulation.py
git commit -m "fix: validate simulation batches before persistence"
```

### Task 2: Close write routes by default

**Files:**
- Modify: `app/routes.py`
- Replace: `tests/test_routes.py`

**Interfaces:**
- `require_app_password` returns HTTP 403 when no configured password matches `X-App-Password`.

- [ ] **Step 1: Write failing tests**

```python
def test_mutating_routes_reject_when_password_is_unconfigured(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "APP_PASSWORD", "")
    assert create_app().test_client().post("/api/simulate").status_code == 403

def test_simulate_accepts_matching_password(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    monkeypatch.setattr(config, "APP_PASSWORD", "secret")
    monkeypatch.setattr("app.routes.run_simulation_batch", lambda _: {"status": "ok"})
    response = create_app().test_client().post("/api/simulate", headers={"X-App-Password": "secret"})
    assert response.get_json() == {"status": "ok"}
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_routes.py -v`

Expected: FAIL because an empty password authorizes requests.

- [ ] **Step 3: Implement minimal protection**

```python
def require_app_password(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        password = config.APP_PASSWORD
        if not password or request.headers.get("X-App-Password", "") != password:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
```

Replace `git add .` with `subprocess.run(["git", "add", "data/world.db", "chronicle"], check=True, capture_output=True)`.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_routes.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routes.py tests/test_routes.py
git commit -m "fix: require password for mutating API routes"
```

### Task 3: Serialize workflows and deploy auto output

**Files:**
- Modify: `.github/workflows/auto.yml`
- Modify: `.github/workflows/simulate.yml`
- Modify: `.github/workflows/historian.yml`
- Create: `tests/test_workflows.py`

- [ ] **Step 1: Write failing workflow tests**

```python
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_state_writing_workflows_share_concurrency_group():
    for name in ("auto.yml", "simulate.yml", "historian.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text()
        assert "group: world-state" in text
        assert "cancel-in-progress: false" in text

def test_auto_deploys_chronicle_to_pages():
    text = (ROOT / ".github" / "workflows" / "auto.yml").read_text()
    assert "actions/deploy-pages@v4" in text
    assert "path: chronicle" in text
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_workflows.py -v`

Expected: FAIL.

- [ ] **Step 3: Update workflow YAML**

Add to each workflow:

```yaml
concurrency:
  group: world-state
  cancel-in-progress: false
```

Make `auto.yml` use `actions/checkout@v4`, `actions/setup-python@v5`, Python 3.11, and permissions `contents`, `pages`, and `id-token` write. After its push step, add the same configure-pages, upload-pages-artifact (`path: chronicle`), and deploy-pages steps as historian.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_workflows.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows tests/test_workflows.py
git commit -m "fix: serialize world workflows and deploy auto chronicles"
```

### Task 4: Align docs and verify regression suite

**Files:**
- Modify: `README.md`
- Modify: `.env.example`

- [ ] **Step 1: Update docs**

Document `GROQ_API_KEY`/numbered Groq keys as primary and Gemini keys as fallback. Remove obsolete Ollama guidance. State that deployed mutation APIs require `APP_PASSWORD`.

- [ ] **Step 2: Run the complete suite**

Run: `pytest -v`

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add README.md .env.example
git commit -m "docs: align LLM and API security configuration"
```

