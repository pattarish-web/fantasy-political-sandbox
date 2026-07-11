# Fantasy Political Sandbox — Design Spec

**Date:** 2026-07-12  
**Status:** Draft for user review  
**Path:** `C:\Users\HygieneTH\Projects\fantasy-political-sandbox`  
**Primary runtime:** GitHub Actions (not local Flask for v1)

## Goal

Simulate a high-fantasy political world with Gemini, persist history in SQLite, turn dramatic rounds into Thai novel chapters, and share readable HTML chronicle files via the GitHub repo.

## Constraints

- User has API keys only in GitHub Actions Secrets (cannot pull secret values to a local machine).
- Personal use: trigger workflows manually (or later on a schedule).
- Share novels as well-formatted HTML files others can open/read.
- Separate from Sangkan marketing/ERP repos (`cleaning-seo-website`, `sangkan-clean`).
- Do not commit real API keys.

## Architecture (v1)

```
fantasy-political-sandbox/
  .github/workflows/
    simulate.yml
    historian.yml
  app/
    __init__.py
    config.py          # model name, paths, load 3 keys from env
    db.py              # SQLite helpers
    gemini_client.py   # key rotation on 429/quota
    simulation.py      # one simulation round
    historian.py       # novel chapter from drama log
    export_html.py     # write chronicle HTML + index
    seed_data.py       # initial characters + locations
  scripts/
    run_simulate.py    # CLI: --rounds N
    run_historian.py   # CLI: write next undrafted drama chapter
  data/
    world.db           # committed so history continues across CI runs
  chronicle/
    index.html
    chapter-NNN.html
  requirements.txt
  README.md
  .gitignore
```

### Data flow

1. **Simulate workflow** loads `GEMINI_API_KEY_1/2/3`, runs N rounds, updates `data/world.db`, commits if at least one round succeeded.
2. **Historian workflow** finds the latest `is_drama=1` log without a matching `chapters` row, generates Thai novel text, saves `chapters`, writes `chronicle/chapter-NNN.html`, regenerates `chronicle/index.html`, commits.
3. Readers open HTML in the repo (browser / raw GitHub preview). GitHub Pages is optional later.

## Database

### `characters`
- `id`, `name` (unique), `faction`, `personality`, `special_power`, `status` (`Alive` | `Dead`)
- Seeded with the existing 20 characters from the prototype.

### `logs`
- `id`, `round_num`, `location`, `p1_name`, `p2_name`, `dialogue_text`, `consequence`, `is_drama`

### `chapters` (new)
- `id`, `round_num` (unique), `title`, `body`, `location`, `p1_name`, `p2_name`, `created_at`
- Prevents rewriting the same drama round.

## GitHub Actions

### Secrets (new repo)

| Name | Purpose |
|------|---------|
| `GEMINI_API_KEY_1` | Primary key |
| `GEMINI_API_KEY_2` | Fallback on 429 |
| `GEMINI_API_KEY_3` | Fallback on 429 |

If only one real key exists initially, the same value may be placed in all three slots (shared quota).

### `simulate.yml`
- Trigger: `workflow_dispatch` with input `rounds` (default 1, allow 1–50).
- Steps: checkout → setup Python → install deps → run `python scripts/run_simulate.py --rounds N` → commit `data/world.db` when changes exist.
- Permissions: `contents: write` for commit.

### `historian.yml`
- Trigger: `workflow_dispatch`.
- Steps: checkout → setup Python → install deps → run `python scripts/run_historian.py` → commit `data/world.db` + `chronicle/**`.

### Commit policy
- Commit at end of job if there is at least one successful unit of work.
- On total failure (all keys rate-limited, etc.), fail the workflow and do not commit a half-broken empty result.

## Gemini client

- Model: `gemini-2.5-flash` (same as prototype; adjustable in config).
- Load non-empty keys from env in order.
- On 429 / too many requests / quota errors: rotate to next key, sleep briefly, retry.
- If all keys fail: raise and fail the script/workflow.
- Simulation requests use JSON MIME type; historian uses plain text.
- JSON parse: strip markdown fences; retry 1–2 times on invalid JSON.

## Novel quality (v1)

- Prompt includes location, both characters (faction, power, personality), dialogue, consequence, and alive/dead status of involved characters.
- Output: literature-grade Thai high-fantasy political chapter.
- Skip if `round_num` already has a chapter.
- No full-series memory across all past chapters in v1 (only current log + character status).

## HTML chronicle

- `chapter-NNN.html`: readable typography, chapter title, meta (round, location, cast), body with comfortable line length and spacing.
- `index.html`: list of chapters with links.
- Encoding UTF-8 for Thai.

## Out of scope (v1)

- Local Flask dashboard (prototype UI deferred).
- Pulling GitHub Actions secret values onto a local machine (impossible by design).
- Automatic GitHub Pages setup.
- Multiplayer / auth / public write access.
- Coupling to `sangkan-clean` or cleaning marketing site.

## Success criteria

1. Fresh clone + Secrets configured → “Run simulate” produces new rows in `world.db` and a commit.
2. After at least one drama log → “Run historian” produces a chapter HTML under `chronicle/` and a commit.
3. Opening `chronicle/index.html` shows a readable list; chapter pages are easy to read in Thai.
4. Forcing a 429 on key 1 (or exhausting it) causes rotation to key 2/3 without manual intervention.
5. README documents Secrets names and how to run both workflows.

## Implementation phases (after plan)

1. Scaffold repo + modules + seed DB + requirements + README.
2. Port simulation + key rotation + historian + HTML export.
3. Add GitHub Actions workflows + commit step.
4. Smoke-test docs; optional later: local CLI dry-run with `.env`, Flask dashboard, Pages.
