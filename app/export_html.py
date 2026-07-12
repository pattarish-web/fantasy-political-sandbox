import html
import urllib.parse
from pathlib import Path

from app import config
from app.db import list_all_characters, get_character_logs


def _chapter_filename(round_num: int) -> str:
    return f"chapter-{int(round_num):03d}.html"


def _body_to_html(body: str) -> str:
    paragraphs = [p.strip() for p in body.replace("\r\n", "\n").split("\n\n")]
    parts = []
    for p in paragraphs:
        if not p:
            continue
        escaped = html.escape(p).replace("\n", "<br>\n")
        parts.append(f"<p>{escaped}</p>")
    return "\n".join(parts) if parts else f"<p>{html.escape(body)}</p>"


def export_chapter(chapter: dict) -> Path:
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    round_num = int(chapter["round_num"])
    title = chapter.get("title", f"บทที่ {round_num}")
    path = config.CHRONICLE_DIR / _chapter_filename(round_num)
    body_html = _body_to_html(chapter.get("body", ""))
    
    p1_name = chapter.get("p1_name", "")
    p2_name = chapter.get("p2_name", "")
    
    images_html = ""
    def get_char_image_html(name):
        if not name: return ""
        import json
        from app.db import get_character_spotlight
        meta_raw = get_character_spotlight(name)
        if not meta_raw: return ""
        try:
            meta = json.loads(meta_raw.get('meta_data', '{}'))
        except:
            meta = {}
        prompts = meta.get('image_prompts', [])
        if prompts:
            prompt = prompts[-1]['prompt']
        else:
            prompt = meta.get('image_prompt')
            
        if prompt:
            safe_prompt = urllib.parse.quote(prompt)
            slug = _char_slug(name)
            url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=400&height=400&nologo=true"
            status = meta_raw.get('status', 'Alive')
            css_filter = "grayscale(100%)" if status == 'Dead' else "none"
            css_border = "border: 4px solid #4a4a4a;" if status == 'Dead' else "border: 4px solid #8b3a2a;"
            
            return f'''
            <div style="text-align: center; margin: 1rem;">
                <img src="{url}" onclick="openLightbox(this.src)" alt="{html.escape(name)}" style="width: 250px; height: 250px; border-radius: 50%; object-fit: cover; {css_border} box-shadow: 0 4px 10px rgba(0,0,0,0.2); filter: {css_filter}; transition: transform 0.2s; cursor: pointer;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                <div style="margin-top: 0.5rem; font-weight: bold; color: #5c1e13;"><a href="char-{slug}.html">{html.escape(name)}</a></div>
            </div>
            '''
        return ""
    
    img1 = get_char_image_html(p1_name)
    img2 = get_char_image_html(p2_name)
    if img1 or img2:
        images_html = f'''
        <div style="margin-top: 3rem; border-top: 1px dashed #d4c2a8; padding-top: 2rem;">
            <h3 style="text-align: center; color: #8b3a2a; margin-bottom: 1.5rem;">ตัวละครในตอนนี้ (คลิกเพื่อดูประวัติ)</h3>
            <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 2rem;">
                {img1}
                {img2}
            </div>
        </div>
        '''
    tone = chapter.get("tone", "neutral").lower()
    
    # Dynamic styling based on tone
    if tone == 'dark':
        bg_col, text_col, link_col, meta_col, border_col = "#1a1a1a", "#e0e0e0", "#ff5252", "#9e9e9e", "#333333"
    elif tone == 'tragic':
        bg_col, text_col, link_col, meta_col, border_col = "#2c2c34", "#d0d0d5", "#64b5f6", "#8e8e93", "#444455"
    elif tone == 'mysterious':
        bg_col, text_col, link_col, meta_col, border_col = "#12121a", "#c8c8d2", "#e040fb", "#7e57c2", "#311b92"
    elif tone == 'epic':
        bg_col, text_col, link_col, meta_col, border_col = "#f5f0e6", "#1c1a17", "#d32f2f", "#5c564c", "#bcaaa4"
    elif tone == 'romantic':
        bg_col, text_col, link_col, meta_col, border_col = "#fff5f8", "#3e2723", "#d81b60", "#ad1457", "#f48fb1"
    else: # neutral
        bg_col, text_col, link_col, meta_col, border_col = "#f7f4ef", "#1c1a17", "#8b3a2a", "#5c564c", "#d4c2a8"

    doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="/static/app.css">
  <style>
    body {{ font-family: "Sarabun", "Noto Sans Thai", Georgia, serif; font-size: 18px; line-height: 1.7;
      max-width: 40rem; margin: 0 auto; padding: 1.25rem; background: {bg_col}; color: {text_col}; transition: background 0.5s; }}
    .meta {{ color: {meta_col}; font-size: 0.95rem; margin-bottom: 1.5rem; }}
    a {{ color: {link_col}; }}
    .nav-bottom {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px dashed {border_col}; text-align: center; margin-bottom: 2rem; }}
    .btn-back {{ display: inline-block; padding: 0.75rem 1.5rem; background: {link_col}; color: #fff !important; text-decoration: none; border-radius: 8px; font-weight: bold; transition: opacity 0.2s, transform 0.1s; border: none; }}
    .btn-back:hover {{ opacity: 0.9; }}
    .btn-back:active {{ transform: scale(0.98); }}
    
    /* Tone Indicator */
    .tone-badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; background: {link_col}33; color: {link_col}; border: 1px solid {link_col}; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 1px; }}
  </style>
</head>
<body>
  <p><a href="index.html">← กลับพงศาวดาร</a></p>
  <div class="tone-badge">{tone}</div>
  <h1 style="color: {link_col};">{html.escape(title)}</h1>
  <div class="meta">
    รอบ {round_num} · {html.escape(chapter.get("location", ""))}<br>
    {html.escape(chapter.get("p1_name", ""))} · {html.escape(chapter.get("p2_name", ""))}
  </div>
  <article>
    {body_html}
  </article>
  
  {images_html}
  
  <div class="nav-bottom">
    <a href="index.html" class="btn-back">⚙️ กลับหน้าหลัก / แผงควบคุม</a>
  </div>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def _char_slug(name: str) -> str:
    import hashlib
    return hashlib.md5(name.encode('utf-8')).hexdigest()[:8]

def export_character_profile(char_data: dict, logs: list[dict]) -> Path:
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
        
    prompts = meta.get('image_prompts', [])
    latest_prompt = prompts[-1]['prompt'] if prompts else meta.get('image_prompt')
    
    gallery_html = ""
    if prompts:
        gallery_html = "<h3 style='margin-top: 2rem;'>📸 แกลเลอรีวิวัฒนาการ (คลิกเพื่อขยาย)</h3><div style='display: flex; gap: 1rem; overflow-x: auto; padding: 1rem 0;'>"
        for p in prompts:
            g_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p['prompt'])}?width=400&height=400&nologo=true"
            g_desc = html.escape(p.get('desc', ''))
            gallery_html += f'''
            <div style="text-align: center; min-width: 150px;">
                <img src="{g_url}" onclick="openLightbox(this.src)" style="width: 150px; height: 150px; border-radius: 10px; object-fit: cover; border: 2px solid #8b3a2a; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'" title="{g_desc}">
                <div style="font-size: 0.8rem; margin-top: 0.5rem;">{g_desc}</div>
            </div>
            '''
        gallery_html += "</div>"

    css_filter = "grayscale(100%)" if char_data['status'] == 'Dead' else "none"
    css_border = "border: 4px solid #4a4a4a;" if char_data['status'] == 'Dead' else "border: 4px solid #8b3a2a;"
    
    aura_css = ""
    if "ตื่นรู้" in char_data.get('special_power', '') or "Awakened" in char_data.get('special_power', ''):
        aura_css = "animation: pulseAura 2s infinite;"

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

    # Fetch artifacts
    artifacts = db.get_artifacts_by_owner(name)
    artifacts_html = ""
    if artifacts:
        items = "".join([f"<li style='margin-bottom: 0.3rem;'>⚔️ <strong>{html.escape(a['name'])}</strong>: {html.escape(a['description'])}</li>" for a in artifacts])
        artifacts_html = f'<div class="meta-row"><span class="meta-label">วัตถุโบราณ:</span><span class="meta-val"><ul style="margin: 0; padding-left: 1.2rem; color: #b71c1c;">{items}</ul></span></div>'

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
    
    @keyframes pulseAura { 0% {box-shadow: 0 0 10px #6a1b9a;} 50% {box-shadow: 0 0 30px #d500f9, 0 0 10px #d500f9 inset;} 100% {box-shadow: 0 0 10px #6a1b9a;} }
    
    /* Lightbox CSS */
    .lightbox { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.9); }
    .lightbox-content { margin: auto; display: block; width: 80%; max-width: 700px; margin-top: 5%; animation: zoom 0.6s; border-radius: 10px; }
    @keyframes zoom { from {transform:scale(0)} to {transform:scale(1)} }
    .close { position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; cursor: pointer; }
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
    <div style="text-align: center; margin-bottom: 1.5rem;">
        {'<img src="https://image.pollinations.ai/prompt/' + urllib.parse.quote(latest_prompt or '') + '?width=400&height=400&nologo=true" onclick="openLightbox(this.src)" style="width: 200px; height: 200px; border-radius: 50%; object-fit: cover; border: 4px solid #8b3a2a; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 1rem; cursor: pointer;">' if latest_prompt else ''}
        <h1 style="border: none; margin-bottom: 0;">{html.escape(name)} {title_html}</h1>
        <div class="status-badge" style="color: {status_color}; margin-top: 0.5rem;">{status_icon} {char_data['status']}</div>
    </div>
    
    <div class="meta-grid">
        <!-- Section 1: Physical & Faction -->
        <div class="meta-section">
            <h3>👤 ข้อมูลทั่วไป & กายภาพ</h3>
            <div class="meta-row"><span class="meta-label">สังกัด:</span><span class="meta-val">{html.escape(char_data.get('faction') or 'ไม่มี')}</span></div>
            <div class="meta-row"><span class="meta-label">เผ่าพันธุ์:</span><span class="meta-val">{_render_meta('race')}</span></div>
            <div class="meta-row"><span class="meta-label">เพศ:</span><span class="meta-val">{_render_meta('gender')}</span></div>
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
            <div class="meta-row"><span class="meta-label">พลังพิเศษ:</span><span class="meta-val" style="color: #6a1b9a; font-weight: bold;">{html.escape(char_data.get('special_power') or 'ไม่มีข้อมูล')}</span></div>
            {artifacts_html}
            <div class="meta-row"><span class="meta-label">รสนิยมทางเพศ:</span><span class="meta-val">{_render_meta('sexuality')}</span></div>
            <div class="meta-row"><span class="meta-label">บุคลิก:</span><span class="meta-val">{html.escape(char_data.get('personality') or 'ไม่มีข้อมูล')}</span></div>
            <div class="meta-row"><span class="meta-label">ฐานะ/ชนชั้น:</span><span class="meta-val">{_render_meta('class_wealth')}</span></div>
            <div class="meta-row"><span class="meta-label">จุดยืน:</span><span class="meta-val">{_render_meta('morality')}</span></div>
            <div class="meta-row"><span class="meta-label">เป้าหมายลับ:</span><span class="meta-val"><strong>{_render_meta('ambition')}</strong></span></div>
            <div class="meta-row"><span class="meta-label">จุดอ่อน:</span><span class="meta-val" style="color: #c62828;">{_render_meta('flaw')}</span></div>
        </div>
    </div>
    
    {gallery_html}
  </div>

  <h2>📜 ประวัติเหตุการณ์ที่ปรากฏตัว</h2>
  <div class="timeline">
    {logs_html}
  </div>
  
  <div class="nav-bottom">
    <a href="index.html" class="btn-back">⚙️ กลับหน้าหลัก / แผงควบคุม</a>
  </div>

  <!-- Lightbox Modal -->
  <div id="myLightbox" class="lightbox" onclick="this.style.display='none'">
    <span class="close">&times;</span>
    <img class="lightbox-content" id="img01">
  </div>
  <script>
  function openLightbox(src) {{
    document.getElementById('myLightbox').style.display = "block";
    document.getElementById('img01').src = src;
  }}
  </script>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def rebuild_index(chapters: list[dict]) -> Path:
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    
    chars = list_all_characters()
    for char in chars:
        logs = get_character_logs(char["name"])
        export_character_profile(char, logs)
        
    char_options = "\n".join([f'<option value="char-{_char_slug(char["name"])}.html">{html.escape(char["name"])}</option>' for char in chars])
    
    path = config.CHRONICLE_DIR / "index.html"
    items = []
    for ch in chapters:
        rn = int(ch["round_num"])
        title = html.escape(ch.get("title", f"บทที่ {rn}"))
        href = _chapter_filename(rn)
        items.append(f'<li><a href="{href}">{title}</a></li>')
    list_html = "\n".join(items) if items else "<li>ยังไม่มีตอนนิยาย</li>"
    doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>พงศาวดาร</title>
  <style>
    :root {{
      --bg: #f7f4ef;
      --text: #1c1a17;
      --accent: #8b3a2a;
      --panel: #ebdcc5;
      --panel-border: #d4c2a8;
      --ok: #2e7d32;
      --warn: #c77c02;
      --error: #c62828;
    }}
    
    body {{
      font-family: "Sarabun", "Noto Sans Thai", Georgia, serif;
      font-size: 18px;
      line-height: 1.7;
      max-width: 40rem;
      margin: 0 auto;
      padding: 1.25rem 1.25rem 5rem;
      background: var(--bg);
      color: var(--text);
    }}
    
    h1, h2, h3 {{
      color: #5c1e13;
      margin-top: 0;
    }}
    
    h1 {{
      border-bottom: 2px solid var(--accent);
      padding-bottom: 0.5rem;
      margin-bottom: 1.5rem;
      font-size: 2rem;
    }}
    
    ul {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    
    .chapter-list a {{
      color: var(--accent);
      display: block;
      padding: 0.85rem 0.5rem;
      text-decoration: none;
      border-bottom: 1px solid var(--panel-border);
      transition: background 0.2s, padding-left 0.2s;
      border-radius: 4px;
    }}
    
    .chapter-list a:hover {{
      background: #ebdcc566;
      padding-left: 0.75rem;
    }}
    
    /* Control Panel Styles */
    .control-panel {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 12px;
      padding: 1.25rem;
      margin-top: 3rem;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    
    .control-panel h2 {{
      font-size: 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }}
    
    .form-group {{
      margin-bottom: 1rem;
    }}
    
    .form-group label {{
      display: block;
      font-size: 0.9rem;
      font-weight: bold;
      margin-bottom: 0.35rem;
      color: #4a4035;
    }}
    
    .input-row {{
      display: flex;
      gap: 0.5rem;
    }}
    
    input[type="password"], input[type="text"] {{
      flex: 1;
      padding: 0.5rem 0.75rem;
      border: 1px solid var(--panel-border);
      border-radius: 6px;
      font-size: 0.95rem;
      background: #fff;
    }}
    
    .btn {{
      padding: 0.65rem 1rem;
      border: 0;
      border-radius: 6px;
      font-weight: bold;
      cursor: pointer;
      font-size: 0.95rem;
      transition: opacity 0.2s, transform 0.1s;
      color: #fff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
    }}
    
    .btn:active {{
      transform: scale(0.98);
    }}
    
    .btn-save {{ background: #4a4035; }}
    .btn-sim {{ background: #1e6091; }}
    .btn-sim10 {{ background: #d97706; }}
    .btn-novel {{ background: var(--accent); }}
    
    .btn:disabled, .btn-disabled {{
      opacity: 0.5;
      cursor: not-allowed;
      transform: none !important;
    }}
    
    .button-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 0.75rem;
      margin-top: 1rem;
    }}
    
    .token-info {{
      font-size: 0.85rem;
      color: #665b4e;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px dashed var(--panel-border);
    }}
    
    .token-info a {{
      color: var(--accent);
      text-decoration: underline;
      cursor: pointer;
    }}
    
    .status-msg {{
      margin-top: 1rem;
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      font-size: 0.9rem;
      display: none;
    }}
    
    .runs-list {{
      margin-top: 1.5rem;
      font-size: 0.85rem;
    }}
    
    .runs-list h3 {{
      font-size: 1rem;
      margin-bottom: 0.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    
    .run-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem;
      border-radius: 4px;
      margin-bottom: 0.35rem;
      background: #fdfcfb;
      border: 1px solid #ebdcc588;
    }}
    
    .run-status {{
      font-weight: bold;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
    }}
    
    .status-completed-success {{ background: #e8f5e9; color: var(--ok); }}
    .status-completed-failure {{ background: #ffebee; color: var(--error); }}
    .status-running {{ background: #e3f2fd; color: #1565c0; animation: pulse 1.5s infinite; }}
    .status-queued {{ background: #fff3e0; color: var(--warn); }}
    
    @keyframes pulse {{
      0% {{ opacity: 0.6; }}
      50% {{ opacity: 1; }}
      100% {{ opacity: 0.6; }}
    }}
    
    /* Lightbox CSS */
    .lightbox {{ display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.9); }}
    .lightbox-content {{ margin: auto; display: block; width: 80%; max-width: 700px; margin-top: 5%; animation: zoom 0.6s; border-radius: 10px; }}
    @keyframes zoom {{ from {{transform:scale(0)}} to {{transform:scale(1)}} }}
    .close {{ position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; cursor: pointer; }}
  </style>
</head>
<body>
  <h1>📚 พงศาวดาร</h1>
  <ul class="chapter-list">
    {list_html}
  </ul>
  
  <div class="control-panel" style="margin-top: 3rem;">
    <h2>👤 ประวัติตัวละคร</h2>
    <div class="form-group">
      <label>เลือกตัวละครเพื่ออ่านประวัติและผลงานที่ผ่านมา:</label>
      <div class="input-row">
        <select id="char-select" style="flex: 1; padding: 0.5rem 0.75rem; border: 1px solid var(--panel-border); border-radius: 6px; font-size: 0.95rem; background: #fff;">
          <option value="" disabled selected>-- เลือกตัวละคร --</option>
          {char_options}
        </select>
        <button class="btn btn-novel" onclick="viewCharacter()">อ่านประวัติ</button>
      </div>
    </div>
    <script>
      function viewCharacter() {{
          const select = document.getElementById('char-select');
          if (select.value) {{
              window.location.href = select.value;
          }}
      }}
    </script>
  </div>

  <!-- Control Panel สำหรับสั่งการจำลองผ่านหน้าเว็บ Static -->
  <div class="control-panel" style="margin-top: 1.5rem;">
    <h2>⚙️ แผงควบคุมพงศาวดาร (GitHub Actions)</h2>
    
    <div id="token-setup-section" style="display: none;">
      <div class="form-group">
        <label>ใส่ GitHub Personal Access Token (Classic) เพื่อสั่งจำลองโลก:</label>
        <div style="font-size: 0.8rem; color: #665b4e; margin-bottom: 0.5rem;">
          Token ต้องการสิทธิ์ <code>repo</code> และ <code>workflow</code> 
          (<a href="https://github.com/settings/tokens/new?scopes=repo,workflow&description=Fantasy%20Political%20Sandbox%20Control%20Panel" target="_blank">สร้าง Token ได้ที่นี่</a>)
        </div>
        <div class="input-row">
          <input type="password" id="gh-token-input" placeholder="ghp_xxxxxxxxxxxx">
          <button class="btn btn-save" onclick="saveToken()">บันทึก</button>
        </div>
      </div>
    </div>
    
    <div id="control-buttons-section" style="display: none;">
      <div class="token-info">
        <span>เชื่อมต่อ GitHub API เรียบร้อย</span>
        <a onclick="deleteToken()">ลบ / เปลี่ยน Token</a>
      </div>
      
      <div class="button-grid">
        <button class="btn btn-sim" id="btn-sim-1" onclick="triggerSim(1)">▶ จำลอง 1 รอบ</button>
        <button class="btn btn-sim10" id="btn-sim-10" onclick="triggerSim(10)">⏩ จำลอง 10 รอบ</button>
        <button class="btn btn-novel" id="btn-novel" onclick="triggerHistorian()">📜 อาลักษณ์แต่งตอนใหม่</button>
        <button class="btn btn-save" id="btn-auto" onclick="triggerAuto()" style="background: #4a4035;">🤖 Auto: 15+1</button>
      </div>
    </div>

    <div class="status-msg" id="status-msg"></div>

    <div class="runs-list">
      <h3>
        <span>⏳ สถานะการประมวลผลล่าสุด</span>
        <button class="btn btn-save" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;" onclick="fetchRuns()">🔄 รีเฟรช</button>
      </h3>
      <div id="runs-list-content">
        <div style="color: #665b4e;">กำลังโหลดสถานะล่าสุด...</div>
      </div>
    </div>
  </div>

  <script>
    const OWNER = "pattarish-web";
    const REPO = "fantasy-political-sandbox";
    
    function getToken() {{
      return localStorage.getItem("fps_github_token") || "";
    }}
    
    function saveToken() {{
      const token = document.getElementById("gh-token-input").value.trim();
      if (!token) return;
      localStorage.setItem("fps_github_token", token);
      document.getElementById("gh-token-input").value = "";
      render();
    }}
    
    function deleteToken() {{
      localStorage.removeItem("fps_github_token");
      render();
    }}
    
    function showStatus(msg, type) {{
      const el = document.getElementById("status-msg");
      if (!el) return;
      el.innerText = msg;
      el.style.display = "block";
      if (type === "ok") {{
        el.style.background = "#e8f5e9";
        el.style.color = "var(--ok)";
      }} else if (type === "warn") {{
        el.style.background = "#fff3e0";
        el.style.color = "var(--warn)";
      }} else {{
        el.style.background = "#ffebee";
        el.style.color = "var(--error)";
      }}
    }}
    
    async function triggerSim(rounds) {{
      toggleButtons(true);
      await runWorkflow("simulate.yml", {{ rounds: String(rounds) }});
      toggleButtons(false);
    }}
    
    async function triggerHistorian() {{
      toggleButtons(true);
      await runWorkflow("historian.yml");
      toggleButtons(false);
    }}

    async function triggerAuto() {{
      toggleButtons(true);
      await runWorkflow("auto.yml");
      toggleButtons(false);
    }}
    
    function toggleButtons(disabled) {{
      ["btn-sim-1", "btn-sim-10", "btn-novel", "btn-auto"].forEach(id => {{
        const btn = document.getElementById(id);
        if (btn) {{
          btn.disabled = disabled;
          if (disabled) btn.classList.add("btn-disabled");
          else btn.classList.remove("btn-disabled");
        }}
      }});
    }}
    
    async function runWorkflow(workflowFile, inputs = {{}}) {{
      const token = getToken();
      if (!token) return;
      showStatus("กำลังส่งคำสั่งไปยัง GitHub Actions...", "warn");
      
      try {{
        const response = await fetch(`https://api.github.com/repos/${{OWNER}}/${{REPO}}/actions/workflows/${{workflowFile}}/dispatches`, {{
          method: "POST",
          headers: {{
            "Authorization": `Bearer ${{token}}`,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
          }},
          body: JSON.stringify({{
            ref: "master",
            inputs: inputs
          }})
        }});
        
        if (response.status === 204) {{
          showStatus("ส่งคำสั่งสำเร็จ! ระบบกำลังเริ่มทำงานใน 10-15 วินาที", "ok");
          setTimeout(fetchRuns, 4000);
        }} else {{
          const data = await response.json().catch(() => ({{}}));
          showStatus(`ล้มเหลว: ${{data.message || response.statusText}}`, "error");
        }}
      }} catch (err) {{
        showStatus(`ข้อผิดพลาด: ${{err.message}}`, "error");
      }}
    }}
    
    async function fetchRuns() {{
      const token = getToken();
      const headers = {{ "Accept": "application/vnd.github+json" }};
      if (token) {{
        headers["Authorization"] = `Bearer ${{token}}`;
      }}
      
      try {{
        const response = await fetch(`https://api.github.com/repos/${{OWNER}}/${{REPO}}/actions/runs?per_page=5`, {{ headers }});
        if (!response.ok) {{
          if (response.status === 401) {{
            document.getElementById("runs-list-content").innerHTML = '<div style="color:var(--error);">Token ไม่ถูกต้องหรือหมดอายุ</div>';
          }}
          return;
        }}
        const data = await response.json();
        const runsList = document.getElementById("runs-list-content");
        if (!runsList) return;
        
        let html = "";
        let hasRunning = false;
        
        for (const run of data.workflow_runs) {{
          let statusClass = "";
          let statusText = "";
          
          if (run.status === "completed") {{
            statusClass = run.conclusion === "success" ? "status-completed-success" : "status-completed-failure";
            statusText = run.conclusion === "success" ? "สำเร็จ ✅" : "ล้มเหลว ❌";
          }} else if (run.status === "in_progress") {{
            statusClass = "status-running";
            statusText = "กำลังรัน ⏳";
            hasRunning = true;
          }} else {{
            statusClass = "status-queued";
            statusText = "รอคิว 💤";
            hasRunning = true;
          }}
          
          const timeStr = new Date(run.created_at).toLocaleTimeString("th-TH", {{ hour: "2-digit", minute: "2-digit" }});
          const nameMap = {{
            "Simulate world rounds": "⚔️ จำลองรอบประวัติศาสตร์",
            "Historian novel chapter": "📜 เรียบเรียงตอนนิยาย"
          }};
          const displayName = nameMap[run.name] || run.name;
          
          html += `
            <div class="run-item">
              <div>
                <strong>${{escapeHtml(displayName)}}</strong>
                <div style="font-size:0.75rem;color:#888;">เริ่มเมื่อ ${{timeStr}}</div>
              </div>
              <span class="run-status ${{statusClass}}">${{statusText}}</span>
            </div>
          `;
        }}
        
        runsList.innerHTML = html || "<div>ไม่มีบันทึกการรัน</div>";
        
        if (hasRunning) {{
          if (!window.runInterval) {{
            window.runInterval = setInterval(fetchRuns, 4000);
          }}
        }} else {{
          if (window.runInterval) {{
            clearInterval(window.runInterval);
            window.runInterval = null;
          }}
        }}
      }} catch (e) {{
        console.error(e);
      }}
    }}
    
    function escapeHtml(str) {{
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }}
    
    function render() {{
      const token = getToken();
      if (token) {{
        document.getElementById("token-setup-section").style.display = "none";
        document.getElementById("control-buttons-section").style.display = "block";
      }} else {{
        document.getElementById("token-setup-section").style.display = "block";
        document.getElementById("control-buttons-section").style.display = "none";
      }}
      fetchRuns();
    }}
    
    render();
  </script>

  <!-- Lightbox Modal -->
  <div id="myLightbox" class="lightbox" onclick="this.style.display='none'">
    <span class="close">&times;</span>
    <img class="lightbox-content" id="img01">
  </div>
  <script>
  function openLightbox(src) {{
    document.getElementById('myLightbox').style.display = "block";
    document.getElementById('img01').src = src;
  }}
  </script>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path
