# Character Image Resilience Design

## Goal

ทำให้หน้าโปรไฟล์ตัวละครแสดงภาพได้ต่อเนื่อง แม้บริการสร้างภาพภายนอกช้าหรือล่ม โดยไม่เปลี่ยนเนื้อเรื่องหรือข้อมูลตัวละคร

## Design

- สร้าง helper กลางสำหรับเลือก URL ภาพ: cache ในเครื่องก่อน, external URL เป็นแหล่งเสริม, placeholder เป็นทางเลือกสุดท้าย
- ทุก `<img>` ต้องมี `alt`, `loading="lazy"` และ `onerror` ที่เปลี่ยนไปยัง fallback ได้เพียงครั้งเดียว
- หากไม่มี image prompt ให้สร้าง prompt สำรองจากชื่อและ metadata
- lightbox ต้องไม่เปิดเมื่อภาพไม่มี `src`

## Success Criteria

- HTML ของตัวละครทุกตัวมี `src` ที่ใช้งานได้หรือ fallback
- รูปเสียไม่ทำให้เห็นวงกลมว่าง
- test ครอบคลุม cache, fallback และ missing prompt
