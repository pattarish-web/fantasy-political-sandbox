import json
import re

from app import db
from app.export_html import export_all_characters, export_chapter, rebuild_index
from app.llm_client import call_llm, clean_json_response
from app.schemas import ChapterResult


MAX_EVENTS_PER_CHAPTER = 3
PRESENT_ACTION_VERBS = ("ยืน", "เดิน", "กล่าว", "ตอบ", "สั่ง", "ยื่น", "ชัก", "ใช้")
MIN_REUSED_DIALOGUE_LENGTH = 20


def _normalize_text(text: str) -> str:
    return " ".join(str(text).split())


def _quoted_lines(text: str) -> set[str]:
    matches = re.findall(r'["“](.{20,}?)[”"]', text, flags=re.DOTALL)
    return {
        normalized
        for match in matches
        if len(normalized := _normalize_text(match)) >= MIN_REUSED_DIALOGUE_LENGTH
    }


def _validate_chapter_continuity(
    body: str,
    state: dict,
    previous_body: str,
    selected_logs: list[dict],
) -> str | None:
    new_deaths = {
        log.get("story_facts", {}).get("character_killed")
        for log in selected_logs
        if log.get("story_facts", {}).get("character_killed")
    }
    for name in set(state.get("deaths", [])) - new_deaths:
        if name in body and any(
            f"{name}{verb}" in body or f"{name} {verb}" in body
            for verb in PRESENT_ACTION_VERBS
        ):
            return f"Canon-dead character acts in present time: {name}"

    if _quoted_lines(body) & _quoted_lines(previous_body):
        return "Chapter reuses dialogue from the previous chapter"
    return None


def _advance_story_state(state: dict, logs: list[dict]) -> dict:
    next_state = {
        key: list(state.get(key, []))
        for key in db.DEFAULT_STORY_STATE
    }
    for log in logs:
        facts = log.get("story_facts", {})
        round_key = f"round:{log['round_num']}"
        if round_key not in next_state["resolved_events"]:
            next_state["resolved_events"].append(round_key)

        killed = facts.get("character_killed")
        if killed and killed not in next_state["deaths"]:
            next_state["deaths"].append(killed)

        war = facts.get("war_declaration")
        if isinstance(war, dict) and war not in next_state["wars"]:
            next_state["wars"].append(war)

        consequence = str(log.get("consequence", "")).strip()
        if consequence:
            next_state["open_threads"].append(
                {"round_num": log["round_num"], "consequence": consequence}
            )

    next_state["open_threads"] = next_state["open_threads"][-6:]
    return next_state


def _format_selected_events(logs: list[dict]) -> tuple[str, set[str]]:
    parts = []
    involved_characters: set[str] = set()
    for idx, log in enumerate(logs, start=1):
        parts.extend(
            [
                f"Event {idx} (Round {log['round_num']}): At {log['location']}",
                f"Characters: {log['p1_name']} and {log['p2_name']}",
                f"Action: {log['consequence']} (Drama: {log['is_drama']})",
                f"Dialogue: {log['dialogue_text']}",
                "-" * 30,
            ]
        )
        involved_characters.update((log["p1_name"], log["p2_name"]))
    return "\n".join(parts), involved_characters


def _format_character_context(names: set[str]) -> str:
    lines = []
    for name in sorted(names):
        character = db.get_character_spotlight(name)
        if character:
            lines.append(
                f"[{name}] Faction: {character.get('faction')} | "
                f"Power: {character.get('special_power')}"
            )
    return "\n".join(lines) or "None"


def _format_earlier_context(first_round: int) -> str:
    earlier_logs = db.get_recent_global_logs_before(first_round, limit=3)
    if not earlier_logs:
        return "None"
    return "\n".join(
        f"- Round {log['round_num']}: {log['p1_name']} vs {log['p2_name']} "
        f"-> {log['consequence']}"
        for log in earlier_logs
    )


def run_historian() -> dict:
    selected_logs = db.get_undrafted_logs(limit=MAX_EVENTS_PER_CHAPTER)
    if not selected_logs:
        return {"message": "nothing to write"}

    target_round = selected_logs[-1]["round_num"]
    selected_context, involved_characters = _format_selected_events(selected_logs)
    state = db.get_story_state()
    chapters = db.list_chapters()
    previous_body = chapters[-1]["body"] if chapters else ""
    prompt = f"""
You are The Grand Historian, writing a Thai fantasy-political novel.

[Selected source events]
{selected_context}

[Earlier world context]
{_format_earlier_context(selected_logs[0]["round_num"])}

[Canonical story state]
{json.dumps(state, ensure_ascii=False)}

[Characters involved]
{_format_character_context(involved_characters)}

[Authoring contract]
- Write in elegant, natural Thai prose.
- Advance exactly one central conflict from the selected events.
- Use no more than two present-time POV characters.
- Show a character making a consequential choice and paying a concrete cost.
- Do not retell resolved events, deaths, or prior dialogue as if they happen now.
- A canon-dead character may appear only as a brief memory or consequence, never as a present-time actor.
- Do not add a death that is not present in the selected source events.
- End with one specific unresolved consequence, not a generic cliffhanger.
- Return a 800-1,200 word chapter and choose one tone: epic, dark, tragic,
  mysterious, romantic, or neutral.

Return strict JSON matching the ChapterResult schema.
"""

    try:
        response_text = call_llm(prompt, response_schema=ChapterResult)
        try:
            result = json.loads(response_text)
        except (TypeError, json.JSONDecodeError):
            result = clean_json_response(response_text)
        if not isinstance(result, dict):
            return {"error": "Historian returned an invalid chapter payload"}

        title = str(result.get("title", "บทนิรนาม")).strip()
        body = str(result.get("body", "")).strip()
        tone = str(result.get("tone", "neutral")).strip().lower()
        if not title or not body:
            return {"error": "Historian returned an empty title or body"}

        continuity_error = _validate_chapter_continuity(
            body,
            state,
            previous_body,
            selected_logs,
        )
        if continuity_error:
            return {"error": continuity_error}

        last_log = selected_logs[-1]
        next_state = _advance_story_state(state, selected_logs)
        db.save_chapter(
            target_round,
            title,
            body,
            last_log["location"],
            last_log["p1_name"],
            last_log["p2_name"],
            tone,
            story_state=next_state,
        )
        chapter = db.get_chapter_by_round(target_round)
        export_chapter(chapter)
        export_all_characters()
        rebuild_index(db.list_chapters())

        return {
            "title": title,
            "novel": body,
            "round_num": target_round,
        }
    except Exception as error:
        return {"error": str(error)}
