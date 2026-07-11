# ใช้ GitHub Secrets อย่างเดียว (ไม่ต้องมี key บนเครื่อง / Render)

Repo: https://github.com/pattarish-web/fantasy-political-sandbox

## 1. ใส่ API Key ใน GitHub Secrets

1. เปิด https://github.com/pattarish-web/fantasy-political-sandbox/settings/secrets/actions
2. **New repository secret** ใส่อย่างใดอย่างหนึ่ง:

| ชื่อ Secret | ใช้เมื่อ |
|-------------|----------|
| `GEMINI_API_KEY` | มี key ตัวเดียว (เหมือน repo `sangkan-clean`) |
| `GEMINI_API_KEY_1` + `_2` + `_3` | มี 3 key สลับตอน 429 |

**หมายเหตุ:** ค่า secret **ดึงจาก repo อื่นมาดูไม่ได้** — ต้อง copy ค่าเดิมที่คุณเก็บไว้ หรือสร้างใหม่ที่ https://aistudio.google.com/apikey

## 2. รันจำลองโลก

1. เปิด **Actions** → **Simulate world rounds** → **Run workflow**
2. ใส่จำนวนรอบ (1 หรือ 10) → **Run**
3. ถ้าสำเร็จ จะ commit `data/world.db` กลับ repo อัตโนมัติ

## 3. แต่งนิยาย + อ่านบนมือถือ

1. **Actions** → **Historian novel chapter** → **Run workflow**
2. ถ้ามีดราม่าที่ยังไม่แต่ง จะสร้าง HTML ใน `chronicle/`
3. เปิด **GitHub Pages** (Settings → Pages → Source: GitHub Actions)
4. URL อ่านนิยาย: `https://pattarish-web.github.io/fantasy-political-sandbox/`

## 4. ตรวจปัญหา

| อาการ | สาเหตุ / แก้ |
|--------|----------------|
| `ไม่พบ API key ใน GitHub Secrets` | ยังไม่ใส่ secret ใน repo นี้ (repo ใหม่ ≠ `sangkan-clean`) |
| `429` / quota | เพิ่ม `GEMINI_API_KEY_2`, `_3` หรือรอ quota |
| Historian บอก `nothing to write` | ยังไม่มี log ดราม่า — รัน Simulate ก่อน |
| Pages ว่าง | รัน Historian สำเร็จ + เปิด Pages source = Actions |

## 5. รัน workflow จากเทอร์มินัล

```powershell
gh workflow run simulate.yml -R pattarish-web/fantasy-political-sandbox -f rounds=1
gh workflow run historian.yml -R pattarish-web/fantasy-political-sandbox
gh run list -R pattarish-web/fantasy-political-sandbox
gh run view <run-id> --log
```
