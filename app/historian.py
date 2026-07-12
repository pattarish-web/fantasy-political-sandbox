import json
import re

from app import db
from app.export_html import export_chapter, rebuild_index
from app.gemini_client import call_gemini


def clean_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _status_for(name: str) -> str:
    alive_names = {row[0] for row in db.get_alive_characters()}
    return "Alive" if name in alive_names else "Dead"


def run_historian() -> dict:
    row = db.get_latest_undrafted_drama()
    if not row:
        return {"message": "nothing to write"}

    round_num, location, p1, p2, dialogue, consequence = row
    p1_meta = db.get_character_spotlight(p1) or {}
    p2_meta = db.get_character_spotlight(p2) or {}
    p1_status = _status_for(p1)
    p2_status = _status_for(p2)
    
    def parse_meta(meta_str):
        try:
            return json.loads(meta_str) if meta_str else {}
        except:
            return {}
            
    p1_meta_parsed = parse_meta(p1_meta.get('meta_data', "{}"))
    p2_meta_parsed = parse_meta(p2_meta.get('meta_data', "{}"))
    
    def format_meta(meta):
        if not meta: return "None"
        lines = []
        if 'str' in meta: lines.append(f"Stats: STR {meta.get('str')}, INT {meta.get('int')}, CHA {meta.get('cha')}, AGI {meta.get('agi')}")
        if 'race' in meta: lines.append(f"Physical: {meta.get('race')} / Age: {meta.get('age')} / {meta.get('height')} / {meta.get('weight')}")
        if 'skills' in meta: lines.append(f"Skills: {meta.get('skills')}")
        if 'weapon' in meta: lines.append(f"Weapon: {meta.get('weapon')}")
        if 'title' in meta: lines.append(f"Title: {meta.get('title')}")
        if 'ambition' in meta: lines.append(f"Ambition: {meta.get('ambition')}")
        if 'flaw' in meta: lines.append(f"Flaw: {meta.get('flaw')}")
        if 'class_wealth' in meta: lines.append(f"Status: {meta.get('class_wealth')} / Morality: {meta.get('morality')}")
        return "\n    ".join(lines)
        
    p1_meta_str = format_meta(p1_meta_parsed)
    p2_meta_str = format_meta(p2_meta_parsed)
    
    recent_global = db.get_recent_global_logs(3)
    global_context = "\n".join([f"- Round {r['round_num']}: {r['p1_name']} vs {r['p2_name']} -> {r['consequence']}" for r in recent_global if r['round_num'] < round_num]) if recent_global else "None"
    
    p1_history = db.get_character_logs(p1)
    p1_context = "\n".join([f"- Round {r['round_num']}: {r['consequence']}" for r in p1_history if r['round_num'] < round_num]) if p1_history else "None"
    
    p2_history = db.get_character_logs(p2)
    p2_context = "\n".join([f"- Round {r['round_num']}: {r['consequence']}" for r in p2_history if r['round_num'] < round_num]) if p2_history else "None"

    # Fetch previous chapter for continuity
    chapters = db.list_chapters()
    prev_chapter_text = "None"
    if chapters:
        last_chap = chapters[-1]
        prev_chapter_text = f"Title: {last_chap['title']}\nSummary of previous events (Read to continue the tone):\n{last_chap['body'][:1000]}... (truncated)"

    prompt = f"""
    You are 'The Grand Historian', an epic high-fantasy novelist.
    Turn this raw simulation log into a beautifully written fantasy political novel chapter (ภาษาไทย).

    IMPORTANT: There is NO fixed protagonist in this world.
    Whoever feels sharper, more consequential, or more vivid in THIS encounter may take the spotlight.
    Prior chronicle appearances (not destiny): {p1}={p1_meta.get('appearances', 0)}, {p2}={p2_meta.get('appearances', 0)}.
    Do not force a permanent hero arc.

    Log (Round {round_num}):
    Location: {location}
    
    Character 1: {p1} (status: {p1_status}, faction: {p1_meta.get('faction', '?')})
    {p1_meta_str}
    {p1}'s Recent History:
    {p1_context}
    
    Character 2: {p2} (status: {p2_status}, faction: {p2_meta.get('faction', '?')})
    {p2_meta_str}
    {p2}'s Recent History:
    {p2_context}
    
    Dialogue: {dialogue}
    Consequence: {consequence}

    [Recent World Events Before This Round]
    {global_context}

    [Previous Chapter Context]
    {prev_chapter_text}

    [{p1}'s Complete History]
    {p1_context}

    [{p2}'s Complete History]
    {p2_context}

    🔥 THE HISTORIAN SUPERPOWERS (RULES) 🔥:
    1. **Dynamic POV & Internal Monologue**: Narrate the chapter emphasizing the Point of View (POV) of the most prominent character in this scene. Dig deep into their Internal Monologue, reflecting their 'Flaw' or 'Ambition'. Let the reader feel their psychology.
    2. **Cinematic Superpowers**: If the 'Consequence' contains any mentions of finding an Artifact, Awakening a new power, or fighting using Elemental Counters, you MUST write that specific scene with majestic, anime-level cinematic grandeur.
    3. **The Cliffhanger**: The final paragraph of the chapter MUST be a gripping cliffhanger, a profound philosophical question, or a suspenseful tease for what's to come next. Keep readers hooked!
    4. **Dynamic Tone**: Determine the emotional tone of this chapter. Pick ONE word: 'epic', 'dark', 'tragic', 'mysterious', 'romantic', or 'neutral'.
    5. **Epic Subtitle**: The chapter title must be grand (e.g. "บทที่ 21: ชื่อตอน - ซับไตเติ้ล").

    - Write it as a complete Epic High-Fantasy Novel Chapter (Long-form, at least 1,000 - 1,500 words).
    - Describe the atmosphere of '{location}', ideological clashes, and mystical/technological power effects in deep detail.
    - VERY IMPORTANT: Connect this chapter seamlessly to the 'Previous Chapter Context' and the recent world events. Do not let it feel disjointed.
    - Use elegant, smooth literature-grade Thai language (นิยายแปลแฟนตาซีฟอร์มยักษ์).
    - Return STRICT JSON: {{"title": "ชื่อตอนภาษาไทย", "body": "เนื้อหาทั้งตอน...", "tone": "epic/dark/tragic/mysterious/romantic/neutral"}}
    """

    try:
        result = None
        last_err = None
        for _ in range(3):
            try:
                text = call_gemini(prompt, as_json=True)
                result = clean_json_response(text)
                if "title" in result and "body" in result:
                    break
                last_err = ValueError("missing title/body")
                result = None
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                last_err = e
                result = None
        if result is None:
            return {"error": f"Invalid JSON from model: {last_err}"}

        title = str(result["title"]).strip()
        body = str(result["body"]).strip()
        tone = str(result.get("tone", "neutral")).strip().lower()
        
        db.save_chapter(round_num, title, body, location, p1, p2, tone)
        chapter = db.get_chapter_by_round(round_num)
        export_chapter(chapter)
        rebuild_index(db.list_chapters())
        return {
            "title": title,
            "novel": body,
            "round_num": round_num,
        }
    except Exception as e:
        return {"error": str(e)}
