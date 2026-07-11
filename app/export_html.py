import html
from pathlib import Path

from app import config


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
    doc = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="/static/app.css">
  <style>
    body {{ font-family: "Sarabun", "Noto Sans Thai", Georgia, serif; font-size: 18px; line-height: 1.7;
      max-width: 40rem; margin: 0 auto; padding: 1.25rem; background: #f7f4ef; color: #1c1a17; }}
    .meta {{ color: #5c564c; font-size: 0.95rem; margin-bottom: 1.5rem; }}
    a {{ color: #8b3a2a; }}
  </style>
</head>
<body>
  <p><a href="index.html">← พงศาวดาร</a></p>
  <h1>{html.escape(title)}</h1>
  <div class="meta">
    รอบ {round_num} · {html.escape(chapter.get("location", ""))}<br>
    {html.escape(chapter.get("p1_name", ""))} · {html.escape(chapter.get("p2_name", ""))}
  </div>
  <article>
    {body_html}
  </article>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def rebuild_index(chapters: list[dict]) -> Path:
    config.CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
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
    body {{ font-family: "Sarabun", "Noto Sans Thai", Georgia, serif; font-size: 18px; line-height: 1.7;
      max-width: 40rem; margin: 0 auto; padding: 1.25rem; background: #f7f4ef; color: #1c1a17; }}
    a {{ color: #8b3a2a; display: block; padding: 0.75rem 0; min-height: 48px; text-decoration: none;
      border-bottom: 1px solid #e0d8cc; }}
  </style>
</head>
<body>
  <h1>พงศาวดาร</h1>
  <ul style="list-style:none;padding:0;margin:0">
    {list_html}
  </ul>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path
