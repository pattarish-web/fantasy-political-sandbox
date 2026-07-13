# Protected World Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restrict reset to confirmed GitHub Actions runs and support restoring a tagged world backup.

**Architecture:** Public and dashboard HTML have no reset path. `reset_world.yml` guards an exact confirmation, tags the pre-reset commit, then resets. `restore_world.yml` validates a backup-tag input, checks out only state paths from the tag, commits, and republishes.

**Tech Stack:** Python, pytest, static HTML export, GitHub Actions, git tags.

## Global Constraints

- Do not change simulation, historian, LLM routing, or story content.
- Reset confirmation is exactly `RESET WORLD`; restore confirmation is exactly `RESTORE WORLD`.
- Restore only `data/world.db`, `chronicle/`, and tracked `story_summary.json`.
- Do not embed secrets or reset credentials in static HTML.

---

### Task 1: Remove reset controls from web interfaces

**Files:** Modify `app/export_html.py`, `templates/mobile_dashboard.html`; test `tests/test_export_html.py` and `tests/test_routes.py`.

- [ ] **Step 1: Write failing assertions**

```python
assert 'id="btn-reset"' not in html
assert 'triggerReset' not in html
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_export_html.py -q`

Expected: FAIL because public output contains a reset button.

- [ ] **Step 3: Remove public and dashboard reset markup/functions**

Remove only reset buttons, reset status copy, and `triggerReset`; retain non-destructive controls and route implementations.

- [ ] **Step 4: Verify green and commit**

Run: `python -m pytest tests/test_export_html.py tests/test_routes.py -q`

Expected: PASS.

Commit: `git add app/export_html.py templates/mobile_dashboard.html tests; git commit -m "fix: remove web reset controls"`

### Task 2: Guard and tag the reset workflow

**Files:** Modify `.github/workflows/reset_world.yml`; test `tests/test_workflows.py`.

- [ ] **Step 1: Write failing workflow assertions**

```python
assert "confirmation:" in reset_world
assert "RESET WORLD" in reset_world
assert "world-backup-" in reset_world
assert "git tag -a" in reset_world
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_workflows.py -q`

Expected: FAIL because confirmation and backup tag are absent.

- [ ] **Step 3: Add workflow dispatch input, guard, tag, and tag push**

```yaml
inputs:
  confirmation:
    required: true
    type: string
```

The guard exits unless `${{ inputs.confirmation }}` equals `RESET WORLD`. The
backup step creates `world-backup-$(date -u +%Y%m%dT%H%M%SZ)` before running the
reset script and pushes the tag.

- [ ] **Step 4: Verify green and commit**

Run: `python -m pytest tests/test_workflows.py -q`

Expected: PASS.

Commit: `git add .github/workflows/reset_world.yml tests/test_workflows.py; git commit -m "feat: protect reset with confirmation and backup"`

### Task 3: Add restore workflow

**Files:** Create `.github/workflows/restore_world.yml`; extend `tests/test_workflows.py`.

- [ ] **Step 1: Write failing assertions**

```python
restore = (root / ".github" / "workflows" / "restore_world.yml").read_text()
assert "RESTORE WORLD" in restore
assert "world-backup-" in restore
assert "git checkout \"$BACKUP_TAG\" -- data/world.db chronicle/" in restore
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_workflows.py -q`

Expected: FAIL because restore workflow is absent.

- [ ] **Step 3: Create restore workflow**

Validate exact confirmation and `world-backup-*` prefix, fetch the tag, verify it
exists, restore only world-state paths, restore/delete `story_summary.json`
according to tag tracking, commit, push, and deploy Pages.

- [ ] **Step 4: Verify complete suite and commit**

Run: `python -m pytest -q`

Expected: PASS.

Commit: `git add .github/workflows/restore_world.yml tests/test_workflows.py; git commit -m "feat: add protected world restore workflow"`

### Task 4: Final verification

- [ ] **Step 1: Verify generated public output has no reset**

Run: `python -m pytest tests/test_export_html.py -q`

Expected: PASS.

- [ ] **Step 2: Verify repository hygiene and workflow references**

Run: `git diff --check && rg -n "RESET WORLD|RESTORE WORLD|world-backup-|triggerReset|btn-reset" .github app templates tests`

Expected: confirmation/tag references only in workflows and tests; no public reset control.
