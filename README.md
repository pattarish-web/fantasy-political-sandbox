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

Create keys at [Google AI Studio](https://aistudio.google.com/apikey).

## ใช้งานหลัก — GitHub Actions + Secrets (ไม่ต้องมี key บนเครื่อง)

1. ใส่ `GEMINI_API_KEY` หรือ `GEMINI_API_KEY_1/2/3` ใน [Repository Secrets](https://github.com/pattarish-web/fantasy-political-sandbox/settings/secrets/actions)
2. **Actions** → **Simulate world rounds** → Run (1 หรือ 10 รอบ)
3. **Actions** → **Historian novel chapter** → Run (แต่งนิยายจากดราม่า)
4. เปิด **Settings → Pages → Source: GitHub Actions** แล้วอ่านที่ Pages URL

รายละเอียดและแก้ปัญหา: [DEPLOY.md](DEPLOY.md)

## Deploy บน Render (ทางเลือก — ต้องใส่ key บนโฮสต์)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pattarish-web/fantasy-political-sandbox)

ใช้เมื่อต้องการปุ่มจำลองบนเว็บแบบ real-time — ต้องใส่ env บน Render แยกจาก GitHub Secrets

## CLI (optional)

```bash
python scripts/run_simulate.py --rounds 1
python scripts/run_historian.py
```

## Tests

```bash
pytest -v
```
