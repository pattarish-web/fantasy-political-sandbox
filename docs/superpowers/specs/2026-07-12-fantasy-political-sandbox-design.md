# Fantasy Political Sandbox — Design Spec

**Date:** 2026-07-12  
**Status:** Ready for user review  
**Path:** `C:\Users\HygieneTH\Projects\fantasy-political-sandbox`  
**Primary runtime:** Hosted Flask web app (mobile-first UI + API)  
**Optional backup:** GitHub Actions CLI workflows  
**GitHub remote:** New private repo (e.g. `pattarish-web/fantasy-political-sandbox`), not `sangkan-clean`

## Goal

Simulate a high-fantasy political world with Gemini, persist history in SQLite, turn dramatic rounds into Thai novel chapters, and let the owner **control and read on a phone** via mobile HTML that has the same action buttons as the PC prototype (simulate 1 / 10, historian).

## Constraints

- API keys live as host environment variables (same three-key rotation idea as GitHub Secrets; values are set on the host, not committed).
- Owner uses the app mainly from a phone browser; others may open chronicle pages to read.
- Separate from Sangkan marketing/ERP repos.
- Do not commit real API keys.

## Architecture (v1)

```
fantasy-political-sandbox/
  .github/workflows/          # optional: simulate.yml, historian.yml
  app/
    __init__.py               # create Flask app
    config.py
    db.py
    gemini_client.py          # key rotation on 429
    simulation.py
    historian.py
    export_html.py
    seed_data.py
    routes.py                 # pages + JSON API
  templates/
    mobile_dashboard.html     # controls + live log (mobile-first; works on PC too)
    chronicle_index.html
    chronicle_chapter.html
  static/
    app.css                   # shared mobile reading + button styles
  scripts/
    run_simulate.py           # CLI for optional Actions
    run_historian.py
  data/
    world.db                  # needs persistent disk on host
  chronicle/                  # also regenerated for static share / Pages backup
  requirements.txt
  README.md
  Procfile / render.yaml      # host boot: gunicorn
  .gitignore
```

### Data flow

1. User opens the hosted site on phone → mobile dashboard shows status + buttons like PC.
2. Tap **จำลอง 1 / 10 รอบ** → `POST /api/simulate` → Gemini → update DB → append to on-page log.
3. Tap **อาลักษณ์หลวง** → `POST /api/historian` → save `chapters` → regenerate chronicle HTML → show chapter / link to read view.
4. Tap **พงศาวดาร** → mobile reading list (`/chronicle`) with large type; chapter pages are phone-optimized.
5. Env on host: `GEMINI_API_KEY_1`, `_2`, `_3`. On 429, rotate keys.

### Why not GitHub Pages alone for buttons

Static Pages cannot call Gemini with secrets. Buttons that actually run simulation need a small backend (Flask on Render/Railway/Fly).

## UI (mobile = primary, PC = same page)

One responsive dashboard (not a separate “PC-only” app):

| Control | Behavior |
|---------|----------|
| รันจำลอง 1 รอบ | Same as prototype |
| รันจำลอง 10 รอบ | Sequential rounds with progress in log |
| อาลักษณ์หลวง | Write latest undrafted drama chapter |
| พงศาวดาร | Navigate to readable chapter index |
| Status strip | Latest round, alive count, active API key index |

Reading pages: soft background, ≥18px type, line-height ~1.7, thumb-friendly chapter list, no horizontal scroll.

## Database

### `characters`
- `id`, `name` (unique), `faction`, `personality`, `special_power`, `status` (`Alive` | `Dead`)
- Seeded with the existing 20 characters from the prototype.

### `logs`
- `id`, `round_num`, `location`, `p1_name`, `p2_name`, `dialogue_text`, `consequence`, `is_drama`

### `chapters`
- `id`, `round_num` (unique), `title`, `body`, `location`, `p1_name`, `p2_name`, `created_at`

## Hosting & secrets

- Deploy Flask with gunicorn to a host that supports **persistent disk** for `data/world.db` (Render disk / Railway volume / Fly volume). Document that ephemeral free instances wipe the DB on restart.
- Set the three Gemini env vars on the host (create keys in AI Studio if GitHub Secrets values are no longer viewable).
- Optional light gate: single shared `APP_PASSWORD` cookie/basic auth so random visitors cannot burn API quota; chronicle read routes may stay public if desired.

## Optional GitHub Actions

Keep CLI + workflows as backup when the host is down:

- Secrets `GEMINI_API_KEY_1/2/3` on the repo
- `simulate.yml` / `historian.yml` commit DB + `chronicle/` 
- Not required for day-to-day phone use

## Gemini client

- Model: `gemini-2.5-flash` (configurable).
- Load non-empty keys from env in order; rotate on 429 / quota; fail if all exhausted.
- Simulation: JSON MIME; historian: JSON `{ "title", "body" }`.
- Invalid JSON: retry 1–2 times.

## Novel quality (v1)

- Prompt includes location, characters (faction, power, personality), dialogue, consequence, alive/dead status.
- Skip if `round_num` already has a chapter.
- No full-series memory across all past chapters in v1.

## Out of scope (v1)

- Pulling secret *values* out of GitHub Actions into the laptop automatically.
- Fancy PWA / offline shell.
- Multiplayer accounts.
- Coupling to Sangkan repos.

## Success criteria

1. Open the hosted URL on a phone → see the same core buttons as the PC prototype and they work.
2. Simulate updates status/log; historian produces a readable chapter page on the phone.
3. Key 1 hitting 429 rotates to key 2/3.
4. DB survives host restart when persistent disk is configured.
5. README covers deploy, env vars, and optional Actions.

## Implementation phases (after plan)

1. Scaffold modules + seed DB + mobile dashboard templates/CSS + API routes.
2. Port simulation, key rotation, historian, chronicle HTML.
3. Add gunicorn/host config + README deploy steps.
4. Optional: GitHub Actions backup workflows.
