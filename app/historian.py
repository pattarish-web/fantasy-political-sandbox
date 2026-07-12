import json

from app import db
from app.export_html import export_chapter, rebuild_index
from app.llm_client import call_llm, clean_json_response
from app.schemas import ChapterResult

def run_historian() -> dict:
    # Fetch ALL undrafted logs, not just drama ones
    with db._connect() as conn:
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT l.round_num, l.location, l.p1_name, l.p2_name, l.dialogue_text, l.consequence, l.is_drama
            FROM logs l
            WHERE NOT EXISTS (SELECT 1 FROM chapters c WHERE c.round_num = l.round_num)
            ORDER BY l.round_num ASC
            """
        )
        undrafted_logs = [dict(row) for row in cur.fetchall()]

    if not undrafted_logs:
        return {"message": "nothing to write"}

    # We will summarize ALL undrafted logs into a single chapter.
    # We take the round_num of the last event as the chapter's official round_num
    target_round = undrafted_logs[-1]["round_num"]
    
    logs_context = ""
    involved_chars = set()
    for idx, log in enumerate(undrafted_logs):
        logs_context += f"Event {idx+1} (Round {log['round_num']}): At {log['location']}\n"
        logs_context += f"Characters: {log['p1_name']} and {log['p2_name']}\n"
        logs_context += f"Action: {log['consequence']} (Drama: {log['is_drama']})\n"
        logs_context += f"Dialogue: {log['dialogue_text']}\n"
        logs_context += "-" * 30 + "\n"
        involved_chars.add(log['p1_name'])
        involved_chars.add(log['p2_name'])

    chars_meta = ""
    for c_name in involved_chars:
        meta = db.get_character_spotlight(c_name)
        if meta:
            chars_meta += f"[{c_name}] Faction: {meta.get('faction')} | Power: {meta.get('special_power')}\n"

    recent_global = db.get_recent_global_logs(3)
    global_context = "\n".join([f"- Round {r['round_num']}: {r['p1_name']} vs {r['p2_name']} -> {r['consequence']}" for r in recent_global if r['round_num'] < target_round]) if recent_global else "None"
    
    chapters = db.list_chapters()
    prev_chapter_text = "None"
    if chapters:
        last_chap = chapters[-1]
        prev_chapter_text = f"Title: {last_chap['title']}\nSummary of previous events (Read to continue the tone):\n{last_chap['body'][:1000]}... (truncated)"

    prompt = f"""
You are 'The Grand Historian', an epic high-fantasy novelist.
Turn the following sequential events into a beautifully written fantasy political novel chapter (ภาษาไทย).

IMPORTANT: There is NO fixed protagonist in this world. 
Write a Multi-POV (Point of View) chapter that weaves these distinct events together into a cohesive storyline.

[The Events to Weave into Chapter]
{logs_context}

[Characters Involved]
{chars_meta}

[Recent World Events Before This Chapter]
{global_context}

[Previous Chapter Context]
{prev_chapter_text}

🔥 THE HISTORIAN SUPERPOWERS (RULES) 🔥:
1. **Dynamic POV Transitions**: Smoothly transition the narrative between different locations and characters as the events occur.
2. **Cinematic Superpowers**: If the events contain artifact discoveries, deaths, or power awakenings, describe them with majestic, anime-level cinematic grandeur.
3. **The Cliffhanger**: The final paragraph MUST be a gripping cliffhanger or a suspenseful tease for what's to come next. Keep readers hooked!
4. **Dynamic Tone**: Determine the emotional tone of this chapter (epic, dark, tragic, mysterious, romantic, or neutral).
5. **Epic Subtitle**: The chapter title must be grand (e.g. "บทที่ X: ชื่อตอน").

- Write it as a complete Epic High-Fantasy Novel Chapter (Long-form, at least 1,000 - 1,500 words).
- Describe the ideological clashes, emotions, and mystical effects in deep detail.
- Connect this chapter seamlessly to the 'Previous Chapter Context'.
- Use elegant, smooth literature-grade Thai language (นิยายแปลแฟนตาซีฟอร์มยักษ์).

Return STRICT JSON matching the ChapterResult schema.
"""

    try:
        text = call_llm(prompt, response_schema=ChapterResult)
        
        try:
            result = json.loads(text)
        except Exception:
            result = clean_json_response(text)

        title = str(result.get("title", "บทนิรนาม")).strip()
        body = str(result.get("body", "...")).strip()
        tone = str(result.get("tone", "neutral")).strip().lower()
        
        # Save chapter associated with the latest round
        # We also just use a representative location/p1/p2 from the last event for the DB index
        last_log = undrafted_logs[-1]
        
        db.save_chapter(target_round, title, body, last_log['location'], last_log['p1_name'], last_log['p2_name'], tone)
        chapter = db.get_chapter_by_round(target_round)
        export_chapter(chapter)
        rebuild_index(db.list_chapters())
        
        return {
            "title": title,
            "novel": body,
            "round_num": target_round,
        }
    except Exception as e:
        return {"error": str(e)}
