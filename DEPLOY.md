# ขึ้นออนไลน์ (Render)

Repo: https://github.com/pattarish-web/fantasy-political-sandbox

## 1. สร้าง Gemini API Key

1. เปิด https://aistudio.google.com/apikey
2. สร้าง key 1–3 ตัว (ใส่ `_1`, `_2`, `_3` บน Render)
3. **ค่าใน GitHub Secrets ดึงลงมาดูไม่ได้** — ต้อง copy ตอนสร้าง หรือสร้างใหม่

## 2. Deploy บน Render

1. เปิด https://dashboard.render.com และล็อกอิน (Connect GitHub)
2. **New +** → **Blueprint**
3. เลือก repo `pattarish-web/fantasy-political-sandbox`
4. Render อ่าน `render.yaml` อัตโนมัติ
5. ใส่ Environment Variables:
   - `GEMINI_API_KEY_1` (จำเป็น)
   - `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3` (ถ้ามี)
   - `APP_PASSWORD` (แนะนำ — กันโดนคนอื่นกดจำลอง)
6. กด **Apply** แล้วรอ deploy เสร็จ
7. เปิด URL ที่ Render ให้บนมือถือ

### ดิสก์ถาวร

`render.yaml` ตั้ง disk ที่ `data/` แล้ว — ประวัติโลก (`world.db`) จะไม่หายเมื่อ restart

## 3. ใช้งาน

- หน้าแรก = แผงควบคุม (จำลอง / อาลักษณ์ / พงศาวดาร)
- ถ้าตั้ง `APP_PASSWORD` แล้ว API ยังไม่ส่งรหัส: เพิ่ม header `X-App-Password: รหัสของคุณ` (หรือปล่อยว่างไว้ก่อน)

## 4. GitHub Actions (ทางเลือก)

ถ้าต้องการ workflow สำรอง ให้รัน:

```powershell
gh auth refresh -h github.com -s workflow
```

แล้ว push โฟลเดอร์ `.github/workflows/` กลับเข้า repo
