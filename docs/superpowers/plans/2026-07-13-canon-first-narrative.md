# Canon-First Narrative Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure each generated chapter advances a validated fantasy-political timeline instead of replaying resolved events.

**Architecture:** Persist each simulation event's narrative facts and a single canonical story ledger in SQLite. Select no more than three undrafted events per chapter, provide only earlier context to the Historian, and reject drafts that resurrect canonical dead characters or reuse prior dialogue.

**Tech Stack:** Python 3.12, Flask, SQLite, Pydantic, pytest.

## Global Constraints

- Preserve existing database worlds; migrations must use `ALTER TABLE` fallbacks.
- Keep LLM provider interfaces and static HTML export interfaces unchanged.
- Use UTF-8 Thai literals and `ensure_ascii=False` for new narrative JSON.
- No dashboard or authentication changes are in scope.

---

### Task 1: Persist canonical narrative state

**Files:**

- Modify: `app/db.py`
- Modify: `tests/test_db.py`

**Interfaces:**

- Produces: `get_story_state() -> dict`, `save_story_state(state: dict) -> None`, `get_undrafted_logs(limit: int) -> list[dict]`, and `get_recent_global_logs_before(round_num: int, limit: int) -> list[dict]`.
- Produces: `save_log(..., story_facts: dict | None = None) -> None`.

- [ ] **Step 1: Write the failing DB tests**

```python
def test_story_state_defaults_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    assert db.get_story_state()["deaths"] == []
    db.save_story_state({"deaths": ["A"], "resolved_events": ["round:1"]})
    assert db.get_story_state()["deaths"] == ["A"]

def test_undrafted_logs_are_limited_and_keep_story_facts(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    for round_num in range(1, 5):
        db.save_log(round_num, "Hall", "A", "B", "d", "c", 1,
                    {"character_killed": "A" if round_num == 1 else None})
    logs = db.get_undrafted_logs(limit=3)
    assert [log["round_num"] for log in logs] == [1, 2, 3]
    assert logs[0]["story_facts"]["character_killed"] == "A"
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& '.\.venv\Scripts\python.exe' -m pytest tests/test_db.py -q`

Expected: FAIL because the story-state functions and `story_facts` argument do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
DEFAULT_STORY_STATE = {
    "deaths": [], "regime_changes": [], "wars": [],
    "resolved_events": [], "open_threads": [],
}

def get_story_state() -> dict:
    # Read row id=1, JSON-decode it, and merge known default keys.

def save_story_state(state: dict) -> None:
    # Upsert row id=1 using json.dumps(state, ensure_ascii=False).
```

Add nullable `story_facts` to `logs` through existing migration-safe `ALTER
TABLE` handling. Decode `story_facts` in `get_undrafted_logs`; use `LIMIT ?`
and ascending round order.

- [ ] **Step 4: Run focused DB tests and verify GREEN**

Run: `& '.\.venv\Scripts\python.exe' -m pytest tests/test_db.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app/db.py tests/test_db.py
git -c user.name=Codex -c user.email=codex@local commit -m "feat: persist narrative canon state"
```

### Task 2: Reject invalid simulation batches before mutation

**Files:**

- Modify: `app/simulation.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**

- Produces: `_validate_encounters(encounters: list[dict], alive_names: set[str]) -> str | None`.
- Consumes: `db.save_log(..., story_facts=...)` from Task 1.

- [ ] **Step 1: Write failing simulation tests**

```python
def test_simulation_rejects_a_dead_character_without_saving_logs(tmp_path, monkeypatch):
    # Seed A and B, mark A Dead, return an encounter containing A.
    result = simulation.run_simulation_batch(1)
    assert "error" in result
    assert db.get_latest_round() == 0

def test_simulation_rejects_a_death_of_nonparticipant_without_saving_logs(tmp_path, monkeypatch):
    # Return A vs B with character_killed="C".
    result = simulation.run_simulation_batch(1)
    assert "error" in result
    assert db.get_latest_round() == 0
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `& '.\.venv\Scripts\python.exe' -m pytest tests/test_simulation.py -q`

Expected: FAIL because invalid encounters are currently persisted.

- [ ] **Step 3: Write minimal implementation**

```python
def _validate_encounters(encounters, alive_names):
    planned_dead = set()
    for encounter in encounters:
        p1, p2 = encounter.get("p1_name"), encounter.get("p2_name")
        if p1 == p2 or p1 not in alive_names - planned_dead or p2 not in alive_names - planned_dead:
            return "Encounter participants must be distinct known living characters"
        killed = encounter.get("character_killed")
        if killed and killed not in {p1, p2}:
            return "A declared death must be one of the encounter participants"
        if killed:
            planned_dead.add(killed)
```

Validate the complete LLM response before the persistence loop. Save a UTF-8
`story_facts` dictionary containing the declared death, war declaration,
relationship update, power awakening, and consequence with each log.

- [ ] **Step 4: Run focused simulation tests and verify GREEN**

Run: `& '.\.venv\Scripts\python.exe' -m pytest tests/test_simulation.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app/simulation.py tests/test_simulation.py
git -c user.name=Codex -c user.email=codex@local commit -m "feat: validate simulation continuity"
```

### Task 3: Compose bounded, canon-aware chapters

**Files:**

- Modify: `app/historian.py`
- Modify: `tests/test_historian.py`

**Interfaces:**

- Consumes: Task 1 DB accessors and state data.
- Produces: `_advance_story_state(state: dict, logs: list[dict]) -> dict` and `_validate_chapter_continuity(body: str, state: dict, previous_body: str, selected_logs: list[dict]) -> str | None`.

- [ ] **Step 1: Write failing Historian tests**

```python
def test_historian_selects_only_three_events_and_keeps_them_out_of_prior_context(tmp_path, monkeypatch):
    # Save four logs, capture the prompt, then run the historian.
    assert "Event 4" not in captured_prompt
    assert "[Earlier world context]" in captured_prompt
    assert "Event 1" not in captured_prompt.split("[Earlier world context]")[1]

def test_historian_rejects_a_canon_dead_character_acting_in_present(tmp_path, monkeypatch):
    db.save_story_state({"deaths": ["A"]})
    # LLM draft contains "A ยืนขึ้นและออกคำสั่ง".
    result = historian.run_historian()
    assert "error" in result
    assert db.get_chapter_by_round(1) is None
```

- [ ] **Step 2: Run focused Historian tests and verify RED**

Run: `& '.\.venv\Scripts\python.exe' -m pytest tests/test_historian.py -q`

Expected: FAIL because the historian currently consumes every undrafted event and accepts the draft.

- [ ] **Step 3: Write minimal implementation**

Use `db.get_undrafted_logs(limit=3)`, load `db.get_story_state()`, and query
prior world context only with rounds before `selected_logs[0]["round_num"]`.
Prompt for Thai prose with one central conflict and at most two present-time
POVs. Include the canon JSON and an explicit no-recap/no-quotation-reuse rule.

```python
PRESENT_ACTION_VERBS = ("ยืน", "เดิน", "กล่าว", "ตอบ", "สั่ง", "ยื่น", "ชัก", "ใช้")

def _validate_chapter_continuity(body, state, previous_body, selected_logs):
    new_deaths = {
        log["story_facts"].get("character_killed")
        for log in selected_logs if log["story_facts"].get("character_killed")
    }
    for name in set(state["deaths"]) - new_deaths:
        if name in body and any(f"{name}{verb}" in body or f"{name} {verb}" in body for verb in PRESENT_ACTION_VERBS):
            return f"Canon-dead character acts in present time: {name}"
    return None
```

Also reject an exact quoted line of at least 20 characters that appears in the
prior chapter. On rejection, return an error before saving a chapter or
advancing the ledger. On success, add selected round keys to `resolved_events`,
append selected death facts and war declarations, and set `open_threads` to
the selected consequences.

- [ ] **Step 4: Run focused Historian tests and verify GREEN**

Run: `& '.\.venv\Scripts\python.exe' -m pytest tests/test_historian.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add app/historian.py tests/test_historian.py
git -c user.name=Codex -c user.email=codex@local commit -m "feat: enforce canon-aware chapter generation"
```

### Task 4: Verify end-to-end regression coverage

**Files:**

- Modify: `README.md`
- Modify: `tests/test_historian.py`

**Interfaces:**

- Documents the chapter-size limit and canon validation behavior.

- [ ] **Step 1: Write an end-to-end regression test**

```python
def test_published_death_is_sent_to_the_next_historian_as_canon(tmp_path, monkeypatch):
    # Publish round 1 with A's death, save a round 2 log, capture the next prompt.
    assert '"deaths": ["A"]' in captured_prompt
```

- [ ] **Step 2: Run test and verify RED if necessary**

Run: `& '.\.venv\Scripts\python.exe' -m pytest tests/test_historian.py -q`

Expected: PASS only after Task 3; if it passes before adding the test, correct the assertion so it proves the required prompt contract.

- [ ] **Step 3: Document the authoring behavior**

Add this README note:

```markdown
### Narrative continuity

Each Historian run writes at most three new world events. Published deaths,
wars, resolved events, and open consequences are retained as canon and passed
to the next chapter, so a later chapter cannot treat a resolved event as new.
```

- [ ] **Step 4: Run the full suite**

Run: `& '.\.venv\Scripts\python.exe' -m pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add README.md tests/test_historian.py
git -c user.name=Codex -c user.email=codex@local commit -m "test: cover narrative continuity regression"
```
