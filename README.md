# Fantasy Political Sandbox

Mobile-first Flask app that simulates a high-fantasy political world with Gemini, then turns dramatic rounds into Thai novel chapters.

## Features

- Dashboard buttons (phone + PC): simulate 1 round, simulate 10 rounds, historian, chronicle
- SQLite world state (`data/world.db`)
- Gemini API key rotation on HTTP 429 / quota (`GEMINI_API_KEY_1` … `_3`)
- Characters spawn continuously (~25% each round + drama-linked births); no fixed protagonist — prominence emerges from events

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

Open `http://127.0.0.1:5000` on desktop or phone (same Wi‑Fi → use your LAN IP).

## Environment

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY_1` | Primary key |
| `GEMINI_API_KEY_2` | Fallback on 429 |
| `GEMINI_API_KEY_3` | Fallback on 429 |
| `GEMINI_MODEL` | Default `gemini-2.5-flash` |
| `APP_PASSWORD` | Optional; if set, mutating APIs require header `X-App-Password` |

Create keys at [Google AI Studio](https://aistudio.google.com/apikey). GitHub Actions secret values cannot be downloaded — mint new keys if you only have them in GitHub Secrets.

## Deploy (Render)

1. Push this repo to GitHub.
2. Create a Render Blueprint from `render.yaml` (or a Web Service manually).
3. Attach a **persistent disk** mounted at the project `data/` directory so `world.db` survives restarts.
4. Set the three Gemini env vars (and optional `APP_PASSWORD`) in the host dashboard.
5. Open the public URL on your phone.

Ephemeral free instances without a disk will wipe the database on restart.

## CLI (optional)

```bash
python scripts/run_simulate.py --rounds 1
python scripts/run_historian.py
```

## Tests

```bash
pytest -v
```
