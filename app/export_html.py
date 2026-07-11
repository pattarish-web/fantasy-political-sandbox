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
    .nav-bottom {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px dashed #d4c2a8; text-align: center; margin-bottom: 2rem; }}
    .btn-back {{ display: inline-block; padding: 0.75rem 1.5rem; background: #8b3a2a; color: #fff !important; text-decoration: none; border-radius: 8px; font-weight: bold; transition: opacity 0.2s, transform 0.1s; }}
    .btn-back:hover {{ opacity: 0.9; }}
    .btn-back:active {{ transform: scale(0.98); }}
  </style>
</head>
<body>
  <p><a href="index.html">← กลับพงศาวดาร</a></p>
  <h1>{html.escape(title)}</h1>
  <div class="meta">
    รอบ {round_num} · {html.escape(chapter.get("location", ""))}<br>
    {html.escape(chapter.get("p1_name", ""))} · {html.escape(chapter.get("p2_name", ""))}
  </div>
  <article>
    {body_html}
  </article>
  
  <div class="nav-bottom">
    <a href="index.html" class="btn-back">⚙️ กลับหน้าหลัก / แผงควบคุม</a>
  </div>
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
  </style>
</head>
<body>
  <h1>📚 พงศาวดาร</h1>
  <ul class="chapter-list">
    {list_html}
  </ul>

  <!-- Control Panel สำหรับสั่งการจำลองผ่านหน้าเว็บ Static -->
  <div class="control-panel">
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
    
    function toggleButtons(disabled) {{
      ["btn-sim-1", "btn-sim-10", "btn-novel"].forEach(id => {{
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
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path
