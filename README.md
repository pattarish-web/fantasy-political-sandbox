# Fantasy Political Sandbox

Mobile-first Flask app that simulates a high-fantasy political world with Groq-first LLM routing, then turns dramatic rounds into Thai novel chapters.

## Features

- Dashboard buttons (phone + PC): simulate 1 round, simulate 10 rounds, historian, chronicle
- SQLite world state (`data/world.db`)
- Groq-first API key rotation on HTTP 429 / quota (`GROQ_API_KEY` + optional `_1` ... `_3`)
- Characters spawn continuously (~25% each round + drama-linked births); no fixed protagonist - prominence emerges from events

## Narrative continuity

Each Historian run writes at most three new world events. Published deaths,
wars, resolved events, and open consequences are retained as canon and passed
to the next chapter, so a later chapter cannot treat a resolved event as new.

## Local run

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env with your keys
python run.py
```

Open `http://127.0.0.1:5000` on desktop or phone (same Wi-Fi -> use your LAN IP).

## Environment

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Primary key |
| `GROQ_API_KEY_1` | Fallback on 429 |
| `GROQ_API_KEY_2` | Fallback on 429 |
| `GROQ_API_KEY_3` | Fallback on 429 |
| `GROQ_MODEL` | Default `llama-3.1-70b-versatile` |
| `GEMINI_API_KEY` | Optional fallback when Groq is unavailable |
| `GEMINI_MODEL` | Default `gemini-2.5-flash` |
| `APP_PASSWORD` | Required for mutating APIs; send it in `X-App-Password` |

Create keys at [Groq](https://console.groq.com/keys) and [Google AI Studio](https://aistudio.google.com/apikey).

## GitHub Actions + Secrets

1. Put `GROQ_API_KEY` or `GROQ_API_KEY_1/2/3` in [Repository Secrets](https://github.com/pattarish-web/fantasy-political-sandbox/settings/secrets/actions)
2. Open **Actions** -> **Simulate world rounds** -> Run (1 or 10 rounds)
3. Open **Actions** -> **Historian novel chapter** -> Run
4. Open **Settings -> Pages -> Source: GitHub Actions** and use the Pages URL

See [DEPLOY.md](DEPLOY.md) for more detail.

## Deploy on Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pattarish-web/fantasy-political-sandbox)

Use this when you want a real-time hosted app and set env vars separately from GitHub Secrets.

## CLI (optional)

```bash
python scripts/run_simulate.py --rounds 1
python scripts/run_simulate.py --rounds 10
python scripts/run_historian.py
```

## Tests

```bash
pytest -v
```
