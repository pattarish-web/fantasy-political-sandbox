# Character Image Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make character images resilient to external image failures without changing story data.

**Architecture:** Add a small HTML image helper in `app/export_html.py`; use deterministic local fallback assets under `static/characters/`; preserve Pollinations as the preferred generated source when available. Add focused pytest coverage for generated markup and missing prompts.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript.

## Global Constraints

- Do not modify story text or character relationships.
- Do not add runtime dependencies.
- Fallback must be deterministic and local.

### Task 1: Add failing image-markup tests

**Files:**
- Test: `tests/test_character_image_resilience.py`

- [ ] Write tests asserting profile markup has `onerror`, `alt`, and a local fallback when prompt is missing.
- [ ] Run `pytest tests/test_character_image_resilience.py -q`; expect failures because helper behavior is absent.

### Task 2: Implement resilient image helper

**Files:**
- Modify: `app/export_html.py`
- Create: `static/characters/placeholder.svg`

- [ ] Add `_character_fallback_url(name)` returning `/fantasy-political-sandbox/static/characters/placeholder.svg`.
- [ ] Add `_image_tag(url, fallback, alt, style, title=None)` emitting escaped attributes, `loading="lazy"`, and one-shot `onerror` fallback.
- [ ] Update profile portrait, gallery, and chapter thumbnails to use the helper.
- [ ] Use a deterministic prompt derived from character name when `latest_prompt` is empty.
- [ ] Guard `openLightbox` against empty sources.

### Task 3: Verify and regenerate

**Files:**
- Modify: generated `chronicle/*.html` only if project workflow requires it.

- [ ] Run focused tests, then full `pytest -q`.
- [ ] Run the project HTML generation/check command and inspect generated pages for fallback markup.
- [ ] Run `git diff --check` and report exact test counts before deploy.
