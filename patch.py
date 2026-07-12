import re

with open('app/export_html.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace everything from def export_character_profile to just before def rebuild_index
pattern = re.compile(r'def export_character_profile.*?def rebuild_index', re.DOTALL)

replacement = '''def export_character_profile(char_data: dict, logs: list[dict]) -> Path:
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    name = char_data["name"]
    filename = f"char-{_char_slug(name)}.html"
    path = config.CHRONICLE_DIR / filename
    
    status_color = "#2e7d32" if char_data["status"] == "Alive" else "#c62828"
    status_icon = "🟢" if char_data["status"] == "Alive" else "💀"
    
    import json
    try:
        meta = json.loads(char_data.get('meta_data', '{}')) if char_data.get('meta_data') else {}
    except:
        meta = {}

    def _render_meta(key, default='-'):
        val = meta.get(key)
        import html
        return html.escape(str(val)) if val else default

    def _stat_bar(label, value, color):
        val = int(value) if value else 0
        return f"""
        <div style="margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.5rem;">
            <strong style="width: 50px; font-size: 0.85rem; color: #665b4e;">{label}</strong>
            <div style="flex-grow: 1; background: #e3d2ba; height: 10px; border-radius: 5px; overflow: hidden;">
                <div style="width: {val}%; background: {color}; height: 100%;"></div>
            </div>
            <span style="width: 30px; text-align: right; font-size: 0.85rem; font-weight: bold;">{val}</span>
        </div>"""

    log_items = []
    import html
    for log in logs:
        is_drama_str = "💥" if log["is_drama"] else "🗣️"
        opponent = log["p1_name"] if log["p2_name"] == name else log["p2_name"]
        opponent_str = f" พบกับ {html.escape(opponent)}" if opponent else ""
        
        log_items.append(f"""
        <div class="log-entry">
            <div class="log-header">
                <span class="log-round">รอบ {log['round_num']}</span>
                <span class="log-location">📍 {html.escape(log['location'])}</span>
                <span class="log-type">{is_drama_str}{opponent_str}</span>
            </div>
            <div class="log-dialogue">{html.escape(log.get('dialogue_text', '')).replace(chr(10), '<br>')}</div>
            <div class="log-consequence"><strong>ผลลัพธ์:</strong> {html.escape(log.get('consequence', ''))}</div>
        </div>
        """)
    
    logs_html = "\\n".join(log_items) if log_items else "<p>ยังไม่มีประวัติในพงศาวดาร</p>"
    
    doc_css = """<style>
    body { font-family: "Sarabun", "Noto Sans Thai", Georgia, serif; font-size: 16px; line-height: 1.7;
      max-width: 50rem; margin: 0 auto; padding: 1.25rem; background: #f7f4ef; color: #1c1a17; }
    a { color: #8b3a2a; }
    .nav-top { margin-bottom: 2rem; }
    .profile-card { background: #ebdcc5; border: 1px solid #d4c2a8; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .profile-card h1 { margin: 0 0 1rem 0; color: #5c1e13; border-bottom: 2px solid #8b3a2a; padding-bottom: 0.5rem; }
    .status-badge { background: #fff; padding: 0.15rem 0.5rem; border-radius: 20px; font-size: 0.9rem; font-weight: bold; border: 1px solid #d4c2a8; display: inline-block; margin-bottom: 1rem; }
    
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1rem; }
    @media (max-width: 600px) { .meta-grid { grid-template-columns: 1fr; } }
    
    .meta-section { background: rgba(255,255,255,0.4); padding: 1rem; border-radius: 8px; border: 1px solid rgba(212,194,168,0.5); }
    .meta-section h3 { margin-top: 0; color: #8b3a2a; font-size: 1.1rem; margin-bottom: 0.8rem; border-bottom: 1px dashed #d4c2a8; padding-bottom: 0.3rem; }
    .meta-row { display: flex; margin-bottom: 0.4rem; font-size: 0.95rem; }
    .meta-label { width: 100px; font-weight: bold; color: #4a4035; flex-shrink: 0; }
    .meta-val { color: #1c1a17; }
    
    h2 { color: #5c1e13; margin-top: 2.5rem; border-bottom: 1px solid #d4c2a8; padding-bottom: 0.5rem; }
    
    .log-entry { background: #fff; border: 1px solid #ebdcc5; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
    .log-header { display: flex; gap: 1rem; font-size: 0.9rem; color: #665b4e; margin-bottom: 0.5rem; border-bottom: 1px dashed #ebdcc5; padding-bottom: 0.5rem; flex-wrap: wrap; }
    .log-round { font-weight: bold; color: #8b3a2a; }
    .log-dialogue { font-style: italic; color: #3a332a; margin-bottom: 0.5rem; padding-left: 1rem; border-left: 3px solid #d4c2a8; }
    .log-consequence { font-size: 0.95rem; }
    
    .nav-bottom { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px dashed #d4c2a8; text-align: center; margin-bottom: 2rem; }
    .btn-back { display: inline-block; padding: 0.75rem 1.5rem; background: #8b3a2a; color: #fff !important; text-decoration: none; border-radius: 8px; font-weight: bold; transition: opacity 0.2s, transform 0.1s; }
    .btn-back:hover { opacity: 0.9; }
    .btn-back:active { transform: scale(0.98); }
  </style>"""

    title_html = f'<span style="font-size: 1.1rem; color: #665b4e;">"{_render_meta("title")}"</span>' if meta.get('title') else ''

    doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ประวัติ: {html.escape(name)}</title>
  <link rel="stylesheet" href="/static/app.css">
  {doc_css}
</head>
<body>
  <div class="nav-top"><a href="index.html">← กลับพงศาวดาร</a></div>
  
  <div class="profile-card">
    <h1>{html.escape(name)} {title_html}</h1>
    <div class="status-badge" style="color: {status_color}">{status_icon} {char_data['status']}</div>
    
    <div class="meta-grid">
        <!-- Section 1: Physical & Faction -->
        <div class="meta-section">
            <h3>👤 ข้อมูลทั่วไป & กายภาพ</h3>
            <div class="meta-row"><span class="meta-label">สังกัด:</span><span class="meta-val">{html.escape(char_data.get('faction') or 'ไม่มี')}</span></div>
            <div class="meta-row"><span class="meta-label">เผ่าพันธุ์:</span><span class="meta-val">{_render_meta('race')}</span></div>
            <div class="meta-row"><span class="meta-label">อายุ:</span><span class="meta-val">{_render_meta('age')}</span></div>
            <div class="meta-row"><span class="meta-label">ส่วนสูง/น้ำหนัก:</span><span class="meta-val">{_render_meta('height')} / {_render_meta('weight')}</span></div>
            <div class="meta-row"><span class="meta-label">สีผิว:</span><span class="meta-val">{_render_meta('skin_color')}</span></div>
            <div class="meta-row"><span class="meta-label">บทบาทรวม:</span><span class="meta-val">{char_data.get('appearances', 0)} ครั้ง</span></div>
        </div>

        <!-- Section 2: RPG Stats -->
        <div class="meta-section">
            <h3>⚔️ ค่าพลังพื้นฐาน</h3>
            {_stat_bar('STR', meta.get('str'), '#c62828')}
            {_stat_bar('INT', meta.get('int'), '#1565c0')}
            {_stat_bar('CHA', meta.get('cha'), '#f57f17')}
            {_stat_bar('AGI', meta.get('agi'), '#2e7d32')}
            
            <div style="margin-top: 1rem; border-top: 1px dashed #d4c2a8; padding-top: 0.5rem;">
                <div class="meta-row"><span class="meta-label" style="width: 60px;">ทักษะ:</span><span class="meta-val">{_render_meta('skills')}</span></div>
                <div class="meta-row"><span class="meta-label" style="width: 60px;">อาวุธ:</span><span class="meta-val">{_render_meta('weapon')}</span></div>
            </div>
        </div>
        
        <!-- Section 3: Narrative & Political -->
        <div class="meta-section" style="grid-column: 1 / -1;">
            <h3>🎭 มิติทางการเมือง & ปูมหลัง</h3>
            <div class="meta-row"><span class="meta-label">พลังพิเศษ:</span><span class="meta-val">{html.escape(char_data.get('special_power') or 'ไม่มีข้อมูล')}</span></div>
            <div class="meta-row"><span class="meta-label">บุคลิก:</span><span class="meta-val">{html.escape(char_data.get('personality') or 'ไม่มีข้อมูล')}</span></div>
            <div class="meta-row"><span class="meta-label">ฐานะ/ชนชั้น:</span><span class="meta-val">{_render_meta('class_wealth')}</span></div>
            <div class="meta-row"><span class="meta-label">จุดยืน:</span><span class="meta-val">{_render_meta('morality')}</span></div>
            <div class="meta-row"><span class="meta-label">เป้าหมายลับ:</span><span class="meta-val"><strong>{_render_meta('ambition')}</strong></span></div>
            <div class="meta-row"><span class="meta-label">จุดอ่อน:</span><span class="meta-val" style="color: #c62828;">{_render_meta('flaw')}</span></div>
        </div>
    </div>
  </div>

  <h2>📜 ประวัติเหตุการณ์ที่ปรากฏตัว</h2>
  <div class="timeline">
    {logs_html}
  </div>
  
  <div class="nav-bottom">
    <a href="index.html" class="btn-back">⚙️ กลับหน้าหลัก / แผงควบคุม</a>
  </div>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def rebuild_index'''

new_text = pattern.sub(replacement, text)

with open('app/export_html.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Patched export_html.py")
