import html
import hashlib
import re
import urllib.parse
from pathlib import Path

from app import config, db
from app.character_data import normalize_display_value, normalize_meta, relationship_type_label, status_label
from app.db import list_all_characters, get_character_logs, get_all_artifacts, get_active_wars, get_all_relationships, get_artifacts_by_owner


def _chapter_filename(round_num: int) -> str:
    return f"chapter-{int(round_num):03d}.html"


def _image_seed(name: str, prompt: str) -> int:
    digest = hashlib.sha256(f"{name}:{prompt}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 999_999 + 1


def _fallback_image_prompt(name: str) -> str:
    return f"{name} character portrait"


def _anime_image_prompt(prompt: str) -> str:
    text = " ".join(str(prompt or "").split())
    if "anime" not in text.lower():
        text = f"Japanese anime style, anime character illustration, {text}"
    return text


def _character_fallback_url() -> str:
    # All published HTML lives under chronicle/, so keep fallback relative to
    # the Pages artifact instead of pointing at the source static directory.
    return "placeholder.svg"


def _image_tag(url: str, fallback: str, alt: str, style: str = "", title: str | None = None) -> str:
    attrs = f' title="{html.escape(title)}"' if title else ""
    safe_alt = html.escape(alt, quote=True)
    safe_url = html.escape(url, quote=True)
    safe_fallback = html.escape(fallback, quote=True)
    return (f'<img src="{safe_url}" alt="{safe_alt}" loading="lazy"{attrs} '
            f'onclick="openLightbox(this.src)" '
            f'onerror="this.onerror=null;this.src=\'{safe_fallback}\';" '
            f'style="{style}">')


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
    
    # In Multi-POV, we don't just rely on p1/p2. We will look for characters in the body.
    import re
    # Find all mentioned characters in the chapter body to show their images
    mentioned = set()
    for name in [row[0] for row in db.get_alive_characters()] + db.get_dead_characters():
        if name in body_html:
            mentioned.add(name)
            
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
            prompt = _anime_image_prompt(meta.get('image_prompt'))
            
        if prompt:
            # Append quality boosters to the prompt
            seed = _image_seed(name, prompt)
            safe_prompt = urllib.parse.quote(prompt + ", masterpiece, best quality, ultra detailed, perfect anatomy")
            neg_prompt = urllib.parse.quote("bad anatomy, missing fingers, extra digits, deformed, floating weapons, broken sword, disfigured, poorly drawn face, poorly drawn hands")
            slug = _char_slug(name)
            url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=200&height=200&nologo=true&model=turbo&negative_prompt={neg_prompt}&seed={seed}"
            status = meta_raw.get('status', 'Alive')
            css_filter = "grayscale(100%)" if status == 'Dead' else "none"
            css_border = "border: 3px solid #4a4a4a;" if status == 'Dead' else "border: 3px solid #8b3a2a;"
            
            fallback_img = _image_tag(url, _character_fallback_url(), name, f"width: 120px; height: 120px; border-radius: 50%; object-fit: cover; {css_border} box-shadow: 0 4px 10px rgba(0,0,0,0.2); filter: {css_filter}; transition: transform 0.2s; cursor: pointer;")
            return f'''
            <div style="text-align: center; margin: 0.5rem; flex: 0 0 auto;">
                {fallback_img}
                <div style="margin-top: 0.5rem; font-weight: bold; font-size: 0.85rem; color: #5c1e13;"><a href="char-{slug}.html">{html.escape(name)}</a></div>
            </div>
            '''
        return ""
    
    img_list = []
    for m in mentioned:
        img_html = get_char_image_html(m)
        if img_html: img_list.append(img_html)
        
    if img_list:
        images_html = f'''
        <div style="margin-top: 3rem; border-top: 1px dashed #d4c2a8; padding-top: 2rem;">
            <h3 style="text-align: center; color: #8b3a2a; margin-bottom: 1.5rem;">ตัวละครเด่นในบทนี้ (คลิกเพื่อดูประวัติ)</h3>
            <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 1rem; overflow-x: auto;">
                {"".join(img_list)}
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
    else: # neutral — keep every published chapter on the unified dark theme
        bg_col, text_col, link_col, meta_col, border_col = "#151821", "#e8eaf0", "#d4af37", "#aeb4c2", "#3a3e49"

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
    เหตุการณ์สิ้นสุดในรอบที่ {round_num}<br>
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
    return hashlib.md5(name.encode('utf-8')).hexdigest()[:8]


def _has_chapter_prefix(title: str) -> bool:
    return bool(re.match(r"^\s*บทที่\s*\d+\s*:", title))

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
    meta = normalize_meta(meta, name)
        
    prompts = meta.get('image_prompts', [])
    latest_prompt = prompts[-1]['prompt'] if prompts else meta.get('image_prompt')
    latest_prompt = _anime_image_prompt(latest_prompt or _fallback_image_prompt(name))
    
    gallery_html = ""
    if prompts:
        gallery_html = "<h3 style='margin-top: 2rem;'>📸 แกลเลอรีวิวัฒนาการ (คลิกเพื่อขยาย)</h3><div style='display: flex; gap: 1rem; overflow-x: auto; padding: 1rem 0;'>"
        for p in prompts:
            portrait_prompt = _anime_image_prompt(p['prompt'])
            seed = _image_seed(name, portrait_prompt)
            safe_prompt = urllib.parse.quote(portrait_prompt + ", masterpiece, highly detailed, cinematic lighting, dramatic, perfect anatomy")
            neg_prompt = urllib.parse.quote("bad anatomy, missing fingers, extra digits, deformed, floating weapons, disfigured, poorly drawn hands")
            g_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=400&height=400&nologo=true&model=turbo&negative_prompt={neg_prompt}&seed={seed}"
            g_desc = html.escape(p.get('desc', ''))
            gallery_html += f'''
            <div style="text-align: center; min-width: 150px;">
                {_image_tag(g_url, _character_fallback_url(), p.get('desc', ''), "width: 150px; height: 150px; border-radius: 10px; object-fit: cover; border: 2px solid #8b3a2a; cursor: pointer; transition: transform 0.2s;", p.get('desc', ''))}
                <div style="font-size: 0.8rem; margin-top: 0.5rem;">{g_desc}</div>
            </div>
            '''
        gallery_html += "</div>"

    css_filter = "grayscale(100%)" if char_data['status'] == 'Dead' else "none"
    css_border = "border: 4px solid #4a4a4a;" if char_data['status'] == 'Dead' else "border: 4px solid #8b3a2a;"
    
    aura_css = ""
    if "ตื่นรู้" in char_data.get('special_power', '') or "Awakened" in char_data.get('special_power', ''):
        aura_css = "animation: pulseAura 2s infinite;"

    def _render_meta(key, default='ข้อมูลยังไม่ระบุ'):
        val = meta.get(key)
        return html.escape(str(normalize_display_value(key, val))) if val else default

    def _stat_bar(label, value, color):
        val = int(value) if value else 0
        return f"""
        <div style="margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.5rem;">
            <strong style="width: 50px; font-size: 0.85rem; color: #aab2c2;">{label}</strong>
            <div style="flex-grow: 1; background: #e3d2ba; height: 10px; border-radius: 5px; overflow: hidden;">
                <div style="width: {val}%; background: {color}; height: 100%;"></div>
            </div>
            <span style="width: 30px; text-align: right; font-size: 0.85rem; font-weight: bold;">{val}</span>
        </div>"""

    # Fetch artifacts
    artifacts = get_artifacts_by_owner(name)
    artifacts_html = ""
    if artifacts:
        items = "".join([f"<li style='margin-bottom: 0.3rem;'>⚔️ <strong>{html.escape(a['name'])}</strong>: {html.escape(a['description'])}</li>" for a in artifacts])
        artifacts_html = f'<div class="meta-row"><span class="meta-label">วัตถุโบราณ:</span><span class="meta-val"><ul style="margin: 0; padding-left: 1.2rem; color: #b71c1c;">{items}</ul></span></div>'

    log_items = []
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
    
    logs_html = "\n".join(log_items) if log_items else "<p>ยังไม่มีประวัติในพงศาวดาร</p>"
    
    doc_css = """<style>
    body { font-family: "Sarabun", "Noto Sans Thai", Georgia, serif; font-size: 16px; line-height: 1.7;
      max-width: 50rem; margin: 0 auto; padding: 1.25rem; background: #090a0f; color: #e0e6ed; }
    a { color: #d4af37; }
    .nav-top { margin-bottom: 2rem; }
    .profile-card { background: #12141c; border: 1px solid rgba(212,175,55,0.45); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 8px 24px rgba(0,0,0,0.35); }
    .profile-card h1 { margin: 0 0 1rem 0; color: #d4af37; border-bottom: 2px solid #d4af37; padding-bottom: 0.5rem; }
    .status-badge { background: #1a1d27; color: #e0e6ed; padding: 0.15rem 0.5rem; border-radius: 20px; font-size: 0.9rem; font-weight: bold; border: 1px solid rgba(255,255,255,0.15); display: inline-block; margin-bottom: 1rem; }
    
    .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1rem; }
    @media (max-width: 600px) { .meta-grid { grid-template-columns: 1fr; } }
    
    .meta-section { background: rgba(255,255,255,0.04); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); }
    .meta-section h3 { margin-top: 0; color: #f5d76e; font-size: 1.1rem; margin-bottom: 0.8rem; border-bottom: 1px dashed rgba(212,175,55,0.35); padding-bottom: 0.3rem; }
    .meta-row { display: flex; margin-bottom: 0.4rem; font-size: 0.95rem; }
    .meta-label { width: 100px; font-weight: bold; color: #aab2c2; flex-shrink: 0; }
    .meta-val { color: #e0e6ed; }
    
    h2 { color: #d4af37; margin-top: 2.5rem; border-bottom: 1px solid rgba(255,255,255,0.12); padding-bottom: 0.5rem; }
    
    .log-entry { background: #171922; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.25); }
    .log-header { display: flex; gap: 1rem; font-size: 0.9rem; color: #aab2c2; margin-bottom: 0.5rem; border-bottom: 1px dashed rgba(255,255,255,0.12); padding-bottom: 0.5rem; flex-wrap: wrap; }
    .log-round { font-weight: bold; color: #d4af37; }
    .log-dialogue { font-style: italic; color: #d8dde8; margin-bottom: 0.5rem; padding-left: 1rem; border-left: 3px solid #d4af37; }
    .log-consequence { font-size: 0.95rem; }
    
    .nav-bottom { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px dashed rgba(255,255,255,0.15); text-align: center; margin-bottom: 2rem; }
    .btn-back { display: inline-block; padding: 0.75rem 1.5rem; background: #d4af37; color: #090a0f !important; text-decoration: none; border-radius: 8px; font-weight: bold; transition: opacity 0.2s, transform 0.1s; }
    .btn-back:hover { opacity: 0.9; }
    .btn-back:active { transform: scale(0.98); }
    
    @keyframes pulseAura { 0% {box-shadow: 0 0 10px #6a1b9a;} 50% {box-shadow: 0 0 30px #d500f9, 0 0 10px #d500f9 inset;} 100% {box-shadow: 0 0 10px #6a1b9a;} }
    
    /* Lightbox CSS */
    .lightbox { display: none; position: fixed; z-index: 999; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.9); user-select: none; -webkit-user-select: none; }
    .lightbox-content { margin: auto; display: block; width: 80%; max-width: 700px; margin-top: 5%; animation: zoom 0.6s; border-radius: 10px; user-select: none; -webkit-user-select: none; -webkit-user-drag: none; }
    @keyframes zoom { from {transform:scale(0)} to {transform:scale(1)} }
    .close { position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; cursor: pointer; }
  </style>"""

    title_html = f'<span style="font-size: 1.1rem; color: #f5d76e;">"{_render_meta("title")}"</span>' if meta.get('title') else ''

    doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(name)} - พงศาวดาร</title>
  <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/app.css">
  {doc_css}
</head>
<body>
  <div class="nav-top"><a href="index.html">← กลับพงศาวดาร</a></div>
  
  <div class="profile-card">
    <div style="text-align: center; margin-bottom: 1.5rem;">
"""
    if latest_prompt:
        seed = _image_seed(name, latest_prompt)
        img_prompt = urllib.parse.quote(latest_prompt + ", masterpiece, best quality, highly detailed, perfect anatomy")
        n_prompt = urllib.parse.quote("bad anatomy, missing fingers, deformed, floating weapons, broken sword, poorly drawn hands")
        char_img_url = f"https://image.pollinations.ai/prompt/{img_prompt}?width=400&height=400&nologo=true&model=turbo&negative_prompt={n_prompt}&seed={seed}"
        portrait = _image_tag(char_img_url, _character_fallback_url(), name, "width: 200px; height: 200px; border-radius: 50%; object-fit: cover; border: 4px solid #d4af37; box-shadow: 0 0 20px rgba(212,175,55,0.3); margin-bottom: 1rem; cursor: pointer;")
        doc += f'<div onclick="openLightbox(this.querySelector(\'img\').src)" style="display:inline-block;">{portrait}</div>\n'

    doc += f"""
        <h1 style="border: none; margin-bottom: 0;">{html.escape(name)} {title_html}</h1>
        <div class="status-badge" style="color: {status_color}; margin-top: 0.5rem;">{status_icon} {html.escape(status_label(char_data['status']))}</div>
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
            {_stat_bar('กำลัง', meta.get('str'), '#c62828')}
            {_stat_bar('ปัญญา', meta.get('int'), '#1565c0')}
            {_stat_bar('เสน่ห์', meta.get('cha'), '#f57f17')}
            {_stat_bar('ว่องไว', meta.get('agi'), '#2e7d32')}
            
            <div style="margin-top: 1rem; border-top: 1px dashed rgba(212,175,55,0.35); padding-top: 0.5rem;">
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


def export_all_characters() -> None:
    from app.db import list_all_characters
    names = [c["name"] for c in list_all_characters()]
    expected_files = {f"char-{_char_slug(name)}.html" for name in names}
    if config.CHRONICLE_DIR.exists():
        for stale in config.CHRONICLE_DIR.glob("char-*.html"):
            if stale.name not in expected_files:
                stale.unlink(missing_ok=True)
    export_updated_characters(names)


def clear_exported_content() -> None:
    import shutil

    if config.CHRONICLE_DIR.exists():
        shutil.rmtree(config.CHRONICLE_DIR)
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    summary = config.ROOT / "story_summary.json"
    if summary.exists():
        summary.unlink()


def export_updated_characters(names: list[str]) -> None:
    from app.db import get_character, get_character_logs
    
    unique_names = set(names)
    for name in unique_names:
        char = get_character(name)
        if char:
            logs = get_character_logs(name)
            export_character_profile(char, logs)


def rebuild_index(chapters: list[dict]) -> Path:
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    
    chars = sorted(
        list_all_characters(),
        key=lambda char: (-int(char.get("appearances", 0) or 0), str(char.get("name", ""))),
    )
    char_options = "\n".join(
        f'<option value="char-{_char_slug(char["name"])}.html">'
        f'{html.escape(char["name"])} — ร่วม {int(char.get("appearances", 0) or 0)} บท</option>'
        for char in chars
    )
    
    path = config.CHRONICLE_DIR / "index.html"
    items = []
    for chapter_index, ch in enumerate(chapters, start=1):
        rn = int(ch["round_num"])
        raw_title = str(ch.get("title") or "").strip()
        if _has_chapter_prefix(raw_title):
            display_title = raw_title
        else:
            display_title = f"บทที่ {chapter_index}: {raw_title or 'ไม่มีชื่อ'}"
        title = html.escape(display_title)
        href = _chapter_filename(rn)
        items.append(f'<li><a href="{href}">{title}</a></li>')
    list_html = "\n".join(items) if items else "<li>ยังไม่มีตอนนิยาย</li>"
    
    # Generate Artifacts HTML
    artifacts = get_all_artifacts()
    if artifacts:
        artifacts_html = "<ul>"
        for art in artifacts:
            artifacts_html += f'<li><strong>{html.escape(art["name"])}</strong> (ครอบครองโดย: <em>{html.escape(art["owner_name"])}</em>) - {html.escape(art["description"])}</li>'
        artifacts_html += "</ul>"
    else:
        artifacts_html = "<p style='color: #665b4e;'>ยังไม่มีอาวุธระดับตำนานปรากฏในโลกนี้...</p>"
        
    # Generate Wars HTML
    wars = get_active_wars()
    if wars:
        wars_html = "<ul>"
        for w in wars:
            wars_html += f'<li>🔥 <strong>{html.escape(w["aggressor_faction"])}</strong> ประกาศสงครามกับ <strong>{html.escape(w["defender_faction"])}</strong> <br>สาเหตุ: {html.escape(w["reason"])}</li>'
        wars_html += "</ul>"
    else:
        wars_html = "<p style='color: #665b4e;'>โลกยังคงสงบสุข... ในตอนนี้</p>"
        
    # Generate Relationships HTML
    rels = get_all_relationships()
    if rels:
        rels_html = "<ul>"
        for r in rels:
            rels_html += f'<li><strong>{html.escape(r["char1"])}</strong> และ <strong>{html.escape(r["char2"])}</strong>: <span style="color: #8b3a2a;">{html.escape(relationship_type_label(r["relationship_type"]))}</span> ({html.escape(r["reason"])})</li>'
        rels_html += "</ul>"
    else:
        rels_html = "<p style='color: #665b4e;'>ยังไม่มีความสัมพันธ์พิเศษก่อตัวขึ้น...</p>"
    doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Grand Chronicles | พงศาวดารแห่งความวุ่นวาย</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&family=Cinzel:wght@500;700&display=swap');
    
    :root {{
      --bg: #090a0f;
      --text: #e0e6ed;
      --accent: #d4af37; /* Gold */
      --accent-glow: rgba(212, 175, 55, 0.4);
      --accent-fire: #e53935; /* Fire Red */
      --panel: rgba(18, 20, 28, 0.65);
      --panel-border: rgba(255, 255, 255, 0.08);
      --ok: #4ade80;
      --warn: #fbbf24;
      --error: #f87171;
    }}
    
    * {{
      box-sizing: border-box;
    }}
    
    body {{
      font-family: "Sarabun", "Noto Sans Thai", sans-serif;
      font-size: 16px;
      line-height: 1.7;
      max-width: 1000px;
      margin: 0 auto;
      padding: 2rem 1.5rem 6rem;
      background: var(--bg);
      background-image: 
        radial-gradient(circle at 15% 50%, rgba(212, 175, 55, 0.03), transparent 25%),
        radial-gradient(circle at 85% 30%, rgba(229, 57, 53, 0.03), transparent 25%);
      color: var(--text);
      min-height: 100vh;
    }}
    
    h1, h2, h3 {{
      font-family: "Cinzel", "Sarabun", serif;
      margin-top: 0;
      font-weight: 700;
    }}
    
    h1 {{
      color: var(--accent);
      text-align: center;
      font-size: 3rem;
      text-transform: uppercase;
      letter-spacing: 2px;
      margin-bottom: 3rem;
      text-shadow: 0 0 20px var(--accent-glow);
    }}
    
    h2 {{
      color: #fff;
      font-size: 1.4rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
      border-bottom: 1px solid var(--panel-border);
      padding-bottom: 0.75rem;
    }}
    
    ul {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    
    .chapter-list {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
      margin-bottom: 4rem;
    }}
    
    .chapter-list a {{
      color: var(--text);
      background: var(--panel);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      display: flex;
      align-items: center;
      padding: 1rem 1.25rem;
      text-decoration: none;
      border: 1px solid var(--panel-border);
      border-left: 3px solid var(--accent);
      border-radius: 8px;
      transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}
    
    .chapter-list a:hover {{
      transform: translateY(-3px);
      background: rgba(255, 255, 255, 0.05);
      border-left-color: var(--accent-fire);
      box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2), 0 0 15px var(--accent-glow);
      color: #fff;
    }}
    
    /* Control Panel Styles */
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }}
    
    @media (max-width: 768px) {{
      .dashboard-grid {{
        grid-template-columns: 1fr;
      }}
    }}
    
    .control-panel {{
      background: var(--panel);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--panel-border);
      border-radius: 16px;
      padding: 1.75rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      position: relative;
      overflow: hidden;
    }}
    
    .control-panel::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    }}
    
    .list-item-box {{
      padding: 0.75rem;
      border-radius: 8px;
      background: rgba(0, 0, 0, 0.3);
      margin-bottom: 0.5rem;
      border: 1px solid rgba(255, 255, 255, 0.03);
      font-size: 0.9rem;
    }}
    
    .list-item-box strong {{
      color: var(--accent);
    }}
    
    .form-group {{
      margin-bottom: 1.25rem;
    }}
    
    .form-group label {{
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
      color: #a0aec0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    
    .input-row {{
      display: flex;
      gap: 0.75rem;
    }}
    
    input[type="password"], input[type="text"], select {{
      flex: 1;
      padding: 0.65rem 1rem;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      font-size: 0.95rem;
      background: rgba(0, 0, 0, 0.5);
      color: #fff;
      font-family: inherit;
      transition: border-color 0.2s;
    }}
    
    input:focus, select:focus {{
      outline: none;
      border-color: var(--accent);
    }}
    
    select option {{
      background: #1a202c;
      color: #fff;
    }}
    
    .btn {{
      padding: 0.65rem 1.25rem;
      border: 1px solid transparent;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.95rem;
      transition: all 0.2s ease;
      color: #fff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      font-family: inherit;
    }}
    
    .btn:active {{
      transform: scale(0.95);
    }}
    
    .btn-save {{ 
      background: rgba(255, 255, 255, 0.1); 
      border-color: rgba(255, 255, 255, 0.2);
    }}
    .btn-save:hover {{ background: rgba(255, 255, 255, 0.2); }}
    
    .btn-sim {{ 
      background: linear-gradient(135deg, #2563eb, #1e40af); 
      box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    }}
    .btn-sim:hover {{ filter: brightness(1.1); box-shadow: 0 4px 20px rgba(37, 99, 235, 0.5); }}
    
    .btn-sim10 {{ 
      background: linear-gradient(135deg, #d97706, #b45309);
      box-shadow: 0 4px 15px rgba(217, 119, 6, 0.3);
    }}
    .btn-sim10:hover {{ filter: brightness(1.1); box-shadow: 0 4px 20px rgba(217, 119, 6, 0.5); }}
    
    .btn-novel {{ 
      background: linear-gradient(135deg, var(--accent), #b49020); 
      color: #000;
      box-shadow: 0 4px 15px var(--accent-glow);
    }}
    .btn-novel:hover {{ filter: brightness(1.1); box-shadow: 0 4px 20px rgba(212, 175, 55, 0.6); }}
    
    .btn-auto {{
      background: linear-gradient(135deg, #e53935, #b71c1c);
      box-shadow: 0 4px 15px rgba(229, 57, 53, 0.3);
    }}
    .btn-auto:hover {{ filter: brightness(1.1); box-shadow: 0 4px 20px rgba(229, 57, 53, 0.5); }}
    
    .btn:disabled, .btn-disabled {{
      opacity: 0.4;
      cursor: not-allowed;
      transform: none !important;
      filter: grayscale(1);
      box-shadow: none !important;
    }}
    
    .button-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
      margin-top: 1rem;
    }}
    
    .token-info {{
      font-size: 0.8rem;
      color: #94a3b8;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px dashed var(--panel-border);
    }}
    
    .token-info a {{
      color: var(--warn);
      text-decoration: none;
      cursor: pointer;
      transition: color 0.2s;
    }}
    .token-info a:hover {{ color: #fff; }}
    
    .status-msg {{
      margin-top: 1.25rem;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 600;
      display: none;
      animation: fadeIn 0.3s;
    }}
    
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(-5px); }} to {{ opacity: 1; transform: none; }} }}
    
    .runs-list {{
      margin-top: 2rem;
    }}
    
    .runs-list h3 {{
      font-size: 1.1rem;
      margin-bottom: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border: none;
      padding: 0;
    }}
    
    .run-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      margin-bottom: 0.5rem;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.05);
      transition: background 0.2s;
    }}
    
    .run-item:hover {{
      background: rgba(0, 0, 0, 0.6);
    }}
    
    .run-status {{
      font-weight: 700;
      font-size: 0.75rem;
      padding: 0.25rem 0.6rem;
      border-radius: 20px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    
    .status-completed-success {{ background: rgba(74, 222, 128, 0.15); color: var(--ok); border: 1px solid rgba(74, 222, 128, 0.3); }}
    .status-completed-failure {{ background: rgba(248, 113, 113, 0.15); color: var(--error); border: 1px solid rgba(248, 113, 113, 0.3); }}
    .status-running {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); animation: pulseStatus 2s infinite; }}
    .status-queued {{ background: rgba(251, 191, 36, 0.15); color: var(--warn); border: 1px solid rgba(251, 191, 36, 0.3); }}
    
    @keyframes pulseStatus {{
      0% {{ box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.4); }}
      70% {{ box-shadow: 0 0 0 6px rgba(56, 189, 248, 0); }}
      100% {{ box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }}
    }}
    
    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: rgba(0,0,0,0.2); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.2); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.4); }}
  </style>
</head>
<body>
  <h1>The Grand Chronicles</h1>
  
  <div class="chapter-list">
    {list_html}
  </div>
  
  <div class="dashboard-grid">
    <!-- Left Column -->
    <div class="grid-col">
      <div class="control-panel">
        <h2>👑 อาวุธระดับตำนาน (Artifacts)</h2>
        <div style="font-size: 0.95rem; margin-top: 1rem; max-height: 250px; overflow-y: auto; padding-right: 5px;">
          {artifacts_html.replace('<li>', '<li class="list-item-box">')}
        </div>
      </div>

      <div class="control-panel" style="margin-top: 1.5rem;">
        <h2>⚔️ สงครามล้างเผ่าพันธุ์ (Active Wars)</h2>
        <div style="font-size: 0.95rem; margin-top: 1rem; max-height: 250px; overflow-y: auto; padding-right: 5px;">
          {wars_html.replace('<li>', '<li class="list-item-box">')}
        </div>
      </div>
      
      <div class="control-panel" style="margin-top: 1.5rem;">
        <h2>🕸️ เครือข่ายความสัมพันธ์</h2>
        <div style="font-size: 0.95rem; margin-top: 1rem; max-height: 250px; overflow-y: auto; padding-right: 5px;">
          {rels_html.replace('<li>', '<li class="list-item-box">')}
        </div>
      </div>
    </div>
    
    <!-- Right Column (Controls) -->
    <div class="grid-col">
      <div class="control-panel" style="border-top: 3px solid var(--accent);">
        <h2>⚙️ แผงควบคุม (แกนระบบ)</h2>
        
        <div class="form-group" style="margin-top: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--panel-border);">
          <label>ค้นหาประวัติตัวละคร</label>
          <div class="input-row">
            <select id="char-select">
              <option value="" disabled selected>-- เลือกตัวละครเพื่ออ่านประวัติ --</option>
              {char_options}
            </select>
            <button class="btn btn-save" onclick="viewCharacter()">อ่านประวัติ</button>
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

        <div id="token-setup-section" style="display: none; margin-top: 1.5rem;">
          <div class="form-group">
            <label>🔑 GitHub Access Token</label>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem;">
              ต้องการสิทธิ์ <code>repo</code> และ <code>workflow</code> 
              (<a href="https://github.com/settings/tokens/new?scopes=repo,workflow&description=Fantasy%20Political%20Sandbox%20Control%20Panel" target="_blank" style="color:var(--accent);">สร้างที่นี่</a>)
            </div>
            <div class="input-row">
              <input type="password" id="gh-token-input" placeholder="ghp_xxxxxxxxxxxx">
              <button class="btn btn-save" onclick="saveToken()">บันทึกรหัส</button>
            </div>
          </div>
        </div>
        
        <div id="control-buttons-section" style="display: none; margin-top: 1.5rem;">
          <div class="token-info">
            <span><span style="color:var(--ok);">●</span> เชื่อมต่อฐานข้อมูล GitHub API สำเร็จ</span>
            <a onclick="deleteToken()">[ ตัดการเชื่อมต่อ ]</a>
          </div>
          
          <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; color: #a0aec0; text-transform: uppercase;">โปรโตคอลคำสั่ง</label>
          <div class="button-grid" style="grid-template-columns: 1fr;">
            <button class="btn btn-auto" id="btn-auto" onclick="triggerAuto()" style="padding: 1rem; font-size: 1.1rem; letter-spacing: 1px;">✨ สร้างตอนอัตโนมัติ (จำลอง 3 เหตุการณ์ + เขียน 1 บท)</button>
            <button class="btn btn-auto" id="btn-openai-auto" onclick="triggerOpenAIAuto()" style="padding: 1rem; font-size: 1.1rem; letter-spacing: 1px; margin-top: .75rem;">🤖 สร้างตอนด้วย OpenAI เท่านั้น</button>
          </div>
        </div>

        <div class="status-msg" id="status-msg"></div>

        <div class="runs-list">
          <h3>
            <span>⏳ สถานะการประมวลผลสด</span>
            <button class="btn btn-save" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;" onclick="fetchRuns()">🔄 Refresh</button>
          </h3>
          <div id="runs-list-content">
            <div style="color: #64748b; padding: 1rem; text-align: center;">กำลังโหลดสถานะ...</div>
          </div>
        </div>
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

    async function triggerOpenAIAuto() {{
      toggleButtons(true);
      await runWorkflow("openai_auto.yml");
      toggleButtons(false);
    }}

    function toggleButtons(disabled) {{
      ["btn-auto", "btn-openai-auto"].forEach(id => {{
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
      if (!token) {{
        showStatus("กรุณาใส่ GitHub token ก่อนสั่งงาน", "warn");
        return;
      }}
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
