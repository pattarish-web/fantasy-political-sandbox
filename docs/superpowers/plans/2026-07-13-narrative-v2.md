# Narrative V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a canon-preserving Thai fantasy-political narrative pipeline with planning, critique, coherent opening chapters, and no simulation backlog.

**Architecture:** Simulation persists typed facts and advances only three events per automatic chapter. The Historian validates a structured chapter plan, drafts prose against a compact world bible and canonical state, critiques it once, then atomically publishes the chapter and updated state. A migration script rewrites the existing reader-facing opening from facts already stored in the world database.

**Tech Stack:** Python 3.12, Flask, SQLite, Pydantic v2, pytest, GitHub Actions, static HTML export.

## Global Constraints

- Preserve existing world records; do not reset `data/world.db`.
- Never publish a chapter when plan, prose, or critique validation fails.
- Reject all resurrection fields; revival is out of scope.
- Auto workflow must create and consume exactly three events per chapter.
- Keep prose and UI strings UTF-8 Thai; no literal replacement-question-mark text.

---

### Task 1: Add typed canonical facts and a compact world bible

**Files:**
- Create: `app/narrative.py`
- Modify: `app/db.py:9-16,174-183,529-555`
- Modify: `app/schemas.py:1-39`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces `WORLD_BIBLE: dict`, `format_world_bible() -> str`, and
  `build_faction_ledger(characters, wars) -> dict`.
- Produces `normalize_story_state(state: dict | None) -> dict` with list and
  mapping values retained by their declared type.

- [ ] **Step 1: Write failing state-normalization and bible tests**

```python
def test_story_state_keeps_typed_facts_and_faction_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "world.db")
    db.init_db()
    db.save_story_state({"relationship_changes": [{"type": "schism"}],
                         "faction_ledger": {"Empire": {"pressure": "high"}}})
    state = db.get_story_state()
    assert state["relationship_changes"] == [{"type": "schism"}]
    assert state["faction_ledger"]["Empire"]["pressure"] == "high"

def test_world_bible_explains_magitech_and_faction_stakes():
    text = narrative.format_world_bible()
    assert "เวทกล" in text
    assert "จักรวรรดิเหล็กกล้า" in text
```

- [ ] **Step 2: Run the targeted tests and observe expected failure**

Run: `python -m pytest tests/test_db.py -q`

Expected: failure because typed keys and `app.narrative` do not exist.

- [ ] **Step 3: Add the minimal typed state and bible implementation**

```python
DEFAULT_STORY_STATE = {
    "deaths": [], "regime_changes": [], "wars": [],
    "resolved_events": [], "open_threads": [], "character_changes": [],
    "relationship_changes": [], "artifacts": [], "faction_ledger": {},
}

def _normalize_story_state(state):
    normalized = copy.deepcopy(DEFAULT_STORY_STATE)
    for key, default in DEFAULT_STORY_STATE.items():
        if isinstance(state, dict) and isinstance(state.get(key), type(default)):
            normalized[key] = state[key]
    return normalized
```

Use `app/narrative.py` for a single `WORLD_BIBLE` constant and deterministic
text formatter; derive a faction ledger from current characters and wars.

- [ ] **Step 4: Run targeted tests and commit**

Run: `python -m pytest tests/test_db.py -q`

Expected: PASS.

Commit: `git commit -am "feat: add typed narrative canon"`

### Task 2: Reject invalid facts and preserve every meaningful world change

**Files:**
- Modify: `app/schemas.py:28-37`
- Modify: `app/simulation.py:46-79,172-205`
- Test: `tests/test_simulation.py`

**Interfaces:**
- `_validate_encounters(encounters: list[dict], alive_names: set[str]) -> str | None`
  rejects a `character_resurrected` key and validates all fact targets.
- `_story_facts(encounter: dict) -> dict` retains death, power, relationship,
  artifact, war, and consequence fields.

- [ ] **Step 1: Write failing validation tests**

```python
def test_validate_encounters_rejects_resurrection():
    encounter = {"p1_name": "A", "p2_name": "B",
                 "character_resurrected": "Dead Hero"}
    error = simulation._validate_encounters([encounter], {"A", "B"})
    assert error == "Resurrection is not supported"

def test_story_facts_keep_artifact_and_relationship_changes():
    facts = simulation._story_facts({"artifact_event": {"type": "create"},
                                     "relationship_update": {"type": "schism"}})
    assert facts["artifact_event"]["type"] == "create"
    assert facts["relationship_update"]["type"] == "schism"
```

- [ ] **Step 2: Run the targeted tests and observe expected failure**

Run: `python -m pytest tests/test_simulation.py -q`

Expected: resurrection is accepted or silently ignored, and omitted facts are
absent.

- [ ] **Step 3: Implement minimal validation and fact serialization**

Remove `character_resurrected` from `EncounterResult`, reject its raw key in
`_validate_encounters`, and extend `_story_facts` without changing any world
record until the entire encounter batch validates.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_simulation.py -q`

Expected: PASS.

Commit: `git commit -am "feat: preserve validated narrative facts"`

### Task 3: Enforce a plan-first, critique-once Historian

**Files:**
- Modify: `app/schemas.py`
- Modify: `app/historian.py`
- Modify: `app/db.py`
- Test: `tests/test_historian.py`

**Interfaces:**
- `ChapterPlan` has `source_rounds`, `pov_characters`, `central_conflict`,
  `political_stake`, `choice`, `cost`, `unresolved_thread`, and `tone`.
- `ChapterCritique` has `approved`, `blocking_issues`, and `rewrite_brief`.
- `_validate_chapter_plan(plan, selected_logs, state) -> str | None` and
  `_validate_chapter_result(body, tone, plan, state, previous_body, logs)`
  return a readable error or `None`.

- [ ] **Step 1: Write failing plan, length, and critique tests**

```python
def test_validate_chapter_plan_rejects_unselected_round():
    plan = {"source_rounds": [99], "pov_characters": ["A"],
            "central_conflict": "c", "political_stake": "s", "choice": "x",
            "cost": "y", "unresolved_thread": "z", "tone": "epic"}
    logs = [{"round_num": 1, "p1_name": "A", "p2_name": "B"}]
    assert historian._validate_chapter_plan(plan, logs, {}) == "Plan uses wrong source rounds"

def test_historian_rewrites_once_after_blocking_critique(tmp_path, monkeypatch):
    # Seed one source log, then return plan, draft, blocked critique, rewrite,
    # and approval from a deterministic fake `call_llm` sequence.
    # Assert the saved title is the rewrite title and fake call count is five.

def test_historian_rejects_body_outside_thai_character_bounds():
    assert historian._validate_chapter_result("สั้น", "epic", plan, {}, "", logs)
```

- [ ] **Step 2: Run the Historian tests and observe expected failure**

Run: `python -m pytest tests/test_historian.py -q`

Expected: missing plan/critique interfaces and currently accepted short prose.

- [ ] **Step 3: Implement the two-stage pipeline**

Use `call_llm(plan_prompt, response_schema=ChapterPlan)` before prose. Require source
rounds to exactly equal the selected log rounds, at most two unique living POV
names, all non-empty conflict fields, and an allowed tone. Require prose to
be 2,400–7,200 non-whitespace Thai characters and forbid ungrounded deaths,
dead present actors, and reused dialogue. Call one `ChapterCritique`; if it
blocks, issue exactly one rewrite request and re-validate before saving.

- [ ] **Step 4: Advance typed state and test it**

Extend `_advance_story_state` to record power, relationship, artifact, and
faction-pressure facts while deduplicating by source round. Include the
character personality and relationships relevant to selected POVs in the
Historian context.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/test_historian.py tests/test_db.py -q`

Expected: PASS.

Commit: `git commit -am "feat: plan and critique narrative chapters"`

### Task 4: Keep the automatic world and chronicle in lockstep

**Files:**
- Modify: `.github/workflows/auto.yml:38`
- Test: `tests/test_workflows.py`

**Interfaces:**
- Automatic job calls `python scripts/run_simulate.py --rounds 3` and one
  Historian pass consumes those three events.

- [ ] **Step 1: Write a failing workflow assertion**

```python
assert "python scripts/run_simulate.py --rounds 3" in auto
assert "--rounds 10" not in auto
```

- [ ] **Step 2: Run the workflow test and observe expected failure**

Run: `python -m pytest tests/test_workflows.py -q`

Expected: failure because the automatic job still creates ten rounds.

- [ ] **Step 3: Change the automatic batch size and verify**

Replace only the automatic workflow argument with `--rounds 3`; leave manual
simulation choices unchanged.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_workflows.py -q`

Expected: PASS.

Commit: `git commit -am "fix: keep automatic chronicle current"`

### Task 5: Replace the contradictory opening and repair reader-facing text

**Files:**
- Create: `scripts/rewrite_canonical_opening.py`
- Modify: `app/db.py`
- Modify: `app/export_html.py`
- Modify: `chronicle/chapter-010.html`
- Modify: `chronicle/chapter-020.html`
- Modify: `chronicle/chapter-030.html`
- Delete: `chronicle/chapter-012.html`
- Modify: `chronicle/index.html`, `chronicle/char-*.html`
- Test: `tests/test_export_html.py`

**Interfaces:**
- `db.replace_chapter(round_num, title, body, tone) -> None` updates only the
  canonical chapter text while preserving its source metadata.
- `scripts/rewrite_canonical_opening.py` rewrites rounds 10, 20, and 30 then
  calls the normal export routines.

- [ ] **Step 1: Write failing export and migration tests**

```python
def test_canonical_opening_rewrites_only_existing_chapter_rows(tmp_path, monkeypatch):
    rewrite_canonical_opening.rewrite_opening()
    assert "บทที่ 1: เพลิงใต้บัลลังก์" in db.get_chapter_by_round(10)["title"]
    assert db.get_chapter_by_round(30)["body"]

def test_exported_reader_pages_have_no_replacement_question_mark_text(tmp_path, monkeypatch):
    export_html.rebuild_index([])
    assert "????" not in (config.CHRONICLE_DIR / "index.html").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run targeted tests and observe expected failure**

Run: `python -m pytest tests/test_export_html.py -q`

Expected: the migration API does not exist and the generated dashboard still
contains replacement-question-mark strings.

- [ ] **Step 3: Implement the canonical retelling and export fixes**

Write three original Thai chapters with the canonical sequence: Lucas dies in
the public confrontation; Valeria breaks with Raizen after choosing soldiers
over an unlawful command; Raizen, Solar, and Cyris die only once as the
religious order turns the succession crisis into war. Use `ผลึกบันทึกภาพ` and
`เครือข่ายเวทกล` for magitech recordings. Replace literal broken UI strings,
include status in `get_character_spotlight`, make image seeds deterministic,
and regenerate all chronicle pages. Remove the obsolete duplicate chapter 12.

- [ ] **Step 4: Run tests and inspect exports**

Run: `python -m pytest tests/test_export_html.py tests/test_db.py -q`

Expected: PASS.

Run: `python scripts/rewrite_canonical_opening.py`

Expected: three canonical chapter pages and an index without `????`.

- [ ] **Step 5: Commit**

Commit: `git commit -am "feat: publish coherent canonical opening"`

### Task 6: Document and verify the complete Narrative V2 release

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-13-narrative-v2-design.md`
- Test: all `tests/`

- [ ] **Step 1: Document the new authoring guarantees and operational flow**

State the three-event cadence, plan/critique retry behavior, canon authority,
and how to run the opening rewrite script.

- [ ] **Step 2: Run complete verification**

Run: `python -m pytest -q`

Expected: all tests pass; record any dependency deprecation warning separately.

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only intended tracked changes before commit.

- [ ] **Step 3: Commit and prepare deployment**

Commit: `git commit -am "docs: explain narrative v2 workflow"`

Merge the feature branch into `master`, push `master`, and confirm the Pages
deployment triggered from the changed `chronicle/` files succeeds.
