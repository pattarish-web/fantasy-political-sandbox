import copy
import json
import re

from pydantic import ValidationError

from app import db, narrative
from app.export_html import export_all_characters, export_chapter, rebuild_index
from app.llm_client import call_llm, clean_json_response
from app.schemas import ChapterCritique, ChapterPlan, ChapterResult


MAX_EVENTS_PER_CHAPTER = 3
ALLOWED_TONES = frozenset({"epic", "dark", "tragic", "mysterious", "romantic", "neutral"})
MIN_BODY_CHARACTERS = 2400
MAX_BODY_CHARACTERS = 7200
PRESENT_ACTION_VERBS = ("ยืน", "เดิน", "กล่าว", "ตอบ", "สั่ง", "ยื่น", "ชัก", "ใช้")
MIN_REUSED_DIALOGUE_LENGTH = 20


def _normalize_plan_tone(plan: ChapterPlan) -> ChapterPlan:
    if plan.tone in ALLOWED_TONES:
        return plan
    print(f"[Historian] Unsupported tone '{plan.tone}', normalized to 'neutral'")
    return plan.model_copy(update={"tone": "neutral"})


def _normalize_text(text: str) -> str:
    return " ".join(str(text).split())


def _quoted_lines(text: str) -> set[str]:
    matches = re.findall(r'["“](.{20,}?)[”"]', text, flags=re.DOTALL)
    return {
        normalized
        for match in matches
        if len(normalized := _normalize_text(match)) >= MIN_REUSED_DIALOGUE_LENGTH
    }


def _load_payload(response_text: str) -> dict:
    try:
        payload = json.loads(response_text)
    except (TypeError, json.JSONDecodeError):
        payload = clean_json_response(response_text)
    return payload if isinstance(payload, dict) else {}


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


def _validate_chapter_plan(
    plan: ChapterPlan,
    selected_logs: list[dict],
    state: dict,
) -> str | None:
    selected_rounds = [log["round_num"] for log in selected_logs]
    if plan.source_rounds != selected_rounds:
        return "Plan uses wrong source rounds"
    if not 1 <= len(plan.pov_characters) <= 2:
        return "Plan must use one or two present-time POV characters"
    if len(set(plan.pov_characters)) != len(plan.pov_characters):
        return "Plan repeats a POV character"

    selected_characters = {
        name
        for log in selected_logs
        for name in (log["p1_name"], log["p2_name"])
    }
    if any(name not in selected_characters for name in plan.pov_characters):
        return "Plan POV uses character outside selected events"
    if any(name in set(state.get("deaths", [])) for name in plan.pov_characters):
        return "Plan uses a canon-dead POV character"
    if plan.tone not in ALLOWED_TONES:
        return "Plan uses unsupported tone"
    for field_name in (
        "central_conflict",
        "political_stake",
        "choice",
        "cost",
        "unresolved_thread",
    ):
        if not getattr(plan, field_name).strip():
            return f"Plan is missing {field_name}"
    return None


def _validate_chapter_result(
    title: str,
    body: str,
    tone: str,
    plan: ChapterPlan,
    state: dict,
    previous_body: str,
    selected_logs: list[dict],
) -> str | None:
    if not title.strip() or not body.strip():
        return "Historian returned an empty title or body"
    if tone not in ALLOWED_TONES or tone != plan.tone:
        return "Chapter tone does not match the approved plan"
    body_length = len(re.sub(r"\s", "", body))
    if not MIN_BODY_CHARACTERS <= body_length <= MAX_BODY_CHARACTERS:
        return "Chapter body is outside the allowed Thai character range"
    return _validate_chapter_continuity(body, state, previous_body, selected_logs)


def _advance_story_state(state: dict, logs: list[dict]) -> dict:
    next_state = db._normalize_story_state(state)
    for log in logs:
        facts = log.get("story_facts", {})
        round_num = log["round_num"]
        round_key = f"round:{round_num}"
        if round_key not in next_state["resolved_events"]:
            next_state["resolved_events"].append(round_key)

        killed = facts.get("character_killed")
        if killed and killed not in next_state["deaths"]:
            next_state["deaths"].append(killed)

        war = facts.get("war_declaration")
        if isinstance(war, dict) and war not in next_state["wars"]:
            next_state["wars"].append(copy.deepcopy(war))

        for key, state_key in (
            ("power_awakened", "character_changes"),
            ("relationship_update", "relationship_changes"),
            ("artifact_event", "artifacts"),
        ):
            fact = facts.get(key)
            if isinstance(fact, dict):
                recorded = {"round_num": round_num, "type": key, **copy.deepcopy(fact)}
                if recorded not in next_state[state_key]:
                    next_state[state_key].append(recorded)

        consequence = str(log.get("consequence", "")).strip()
        if consequence:
            thread = {"round_num": round_num, "status": "open", "consequence": consequence}
            if thread not in next_state["open_threads"]:
                next_state["open_threads"].append(thread)

    next_state["open_threads"] = next_state["open_threads"][-12:]
    next_state["faction_ledger"] = narrative.build_faction_ledger(
        db.list_all_characters(), db.get_active_wars()
    )
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
                f"Facts: {json.dumps(log.get('story_facts', {}), ensure_ascii=False)}",
                "-" * 30,
            ]
        )
        involved_characters.update((log["p1_name"], log["p2_name"]))
    return "\n".join(parts), involved_characters


def _format_character_context(names: set[str]) -> str:
    relationships = db.get_all_relationships()
    lines = []
    for name in sorted(names):
        character = db.get_character_spotlight(name)
        if not character:
            continue
        character_relationships = [
            f"{row['char1']}–{row['char2']}: {row['relationship_type']}"
            for row in relationships
            if name in (row["char1"], row["char2"])
        ]
        lines.append(
            f"[{name}] Faction: {character.get('faction')} | "
            f"Personality: {character.get('personality')} | "
            f"Power: {character.get('special_power')} | "
            f"Relationships: {'; '.join(character_relationships) or 'None'}"
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


def _request_plan_once(selected_context: str, state: dict, character_context: str, correction: str = "") -> ChapterPlan:
    prompt = f"""
You are the planning editor for a Thai fantasy-political novel.

[Selected source events]
{selected_context}

[Canonical story state]
{json.dumps(state, ensure_ascii=False)}

[World bible]
{narrative.format_world_bible()}

[Characters involved]
{character_context}

Plan exactly one chapter using every selected source round in order. Choose one
or two living present-time POV characters from the selected events. State the
central conflict, political stake, consequential choice, concrete cost, and a
specific unresolved thread. Never invent a death or resurrection.
{correction}
"""
    return ChapterPlan.model_validate(_load_payload(call_llm(prompt, response_schema=ChapterPlan)))


def _request_plan_with_retry(selected_context: str, state: dict, character_context: str) -> ChapterPlan:
    correction = ""
    last_error = None
    for _ in range(3):
        try:
            return _normalize_plan_tone(_request_plan_once(selected_context, state, character_context, correction))
        except ValidationError as error:
            last_error = error
            correction = (
                "Previous JSON failed validation. Return every required field, including "
                "tone, and make source_rounds an array of integers only. Error: " + str(error)
            )
    # Deterministic last resort: preserve the selected events and canon while
    # letting the prose model continue. This is not a new plot event.
    rounds = [int(value) for value in re.findall(r"Event \d+ \(Round (\d+)\)", selected_context)]
    participants = []
    for first, second in re.findall(r"Characters: (.+?) and (.+)", selected_context):
        for name in (first.strip(), second.strip()):
            if name not in participants:
                participants.append(name)
    if not rounds or len(participants) == 0:
        raise last_error
    return ChapterPlan(
        source_rounds=rounds,
        pov_characters=participants[:2],
        central_conflict="ผลกระทบทางการเมืองจากเหตุการณ์ล่าสุด",
        political_stake="ความมั่นคงของดินแดนและความไว้วางใจระหว่างฝ่าย",
        choice="ตัวละครต้องเลือกท่าทีต่อเหตุการณ์",
        cost="การเลือกครั้งนี้ทำให้ความสัมพันธ์ทางการเมืองเปลี่ยนไป",
        unresolved_thread="ผลลัพธ์ของการตัดสินใจยังไม่คลี่คลาย",
        tone="neutral",
    )


def _request_chapter(
    plan: ChapterPlan,
    selected_context: str,
    state: dict,
    character_context: str,
    earlier_context: str,
    rewrite_brief: str = "",
    draft: ChapterResult | None = None,
) -> ChapterResult:
    draft_context = ""
    if draft:
        draft_context = f"""
[Draft requiring revision]
Title: {draft.title}
Body:
{draft.body}

[Required revision]
{rewrite_brief}
"""
    prompt = f"""
You are The Grand Historian, writing a Thai fantasy-political novel.

[Approved chapter plan]
{plan.model_dump_json(ensure_ascii=False)}

[Selected source events]
{selected_context}

[Earlier world context]
{earlier_context}

[Canonical story state]
{json.dumps(state, ensure_ascii=False)}

[World bible]
{narrative.format_world_bible()}

[Characters involved]
{character_context}
{draft_context}
[Authoring contract]
- Write elegant, natural Thai prose in 2,400–7,200 non-whitespace characters.
- Follow the approved plan and its one central conflict exactly.
- Use no more than two present-time POV characters.
- Show the approved choice and its concrete cost through scene, action, and dialogue.
- Do not retell resolved events, deaths, or prior dialogue as if they happen now.
- A canon-dead character may appear only as memory or consequence, never as a present-time actor.
- Do not add a death or resurrection outside selected source facts.
- End with the approved specific unresolved consequence.
"""
    return ChapterResult.model_validate(
        _load_payload(call_llm(prompt, response_schema=ChapterResult))
    )


def _request_critique(
    plan: ChapterPlan,
    chapter: ChapterResult,
    state: dict,
) -> ChapterCritique:
    prompt = f"""
You are a strict Thai fiction editor. Assess this draft against the approved
plan and canon. Block the draft if continuity, causality, political clarity,
character voice, or repetition would harm readers. If blocked, give one short,
actionable rewrite brief. Do not rewrite prose yourself.

[Plan]
{plan.model_dump_json(ensure_ascii=False)}

[Canon]
{json.dumps(state, ensure_ascii=False)}

[Draft]
Title: {chapter.title}
Body:
{chapter.body}
"""
    return ChapterCritique.model_validate(
        _load_payload(call_llm(prompt, response_schema=ChapterCritique))
    )


def _validate_and_critique(
    chapter: ChapterResult,
    plan: ChapterPlan,
    state: dict,
    previous_body: str,
    selected_logs: list[dict],
) -> tuple[str | None, ChapterCritique | None]:
    error = _validate_chapter_result(
        chapter.title,
        chapter.body,
        chapter.tone,
        plan,
        state,
        previous_body,
        selected_logs,
    )
    if error:
        return error, None
    critique = _request_critique(plan, chapter, state)
    if not critique.approved and not critique.rewrite_brief.strip():
        return "Critique rejected the chapter without a rewrite brief", None
    return None, critique


def run_historian() -> dict:
    selected_logs = db.get_undrafted_logs(limit=MAX_EVENTS_PER_CHAPTER)
    if not selected_logs:
        return {"message": "nothing to write"}

    target_round = selected_logs[-1]["round_num"]
    selected_context, involved_characters = _format_selected_events(selected_logs)
    state = db.get_story_state()
    chapters = db.list_chapters()
    previous_body = chapters[-1]["body"] if chapters else ""
    character_context = _format_character_context(involved_characters)
    earlier_context = _format_earlier_context(selected_logs[0]["round_num"])

    try:
        plan = _request_plan_with_retry(selected_context, state, character_context)
        plan_error = _validate_chapter_plan(plan, selected_logs, state)
        if plan_error:
            return {"error": plan_error}

        chapter = _request_chapter(
            plan, selected_context, state, character_context, earlier_context
        )
        # Ask the model to expand/shorten only when the prose length contract
        # is violated; canon and narrative checks remain unchanged.
        for attempt in range(2):
            length_error = _validate_chapter_result(
                chapter.title, chapter.body, chapter.tone, plan, state,
                previous_body, selected_logs
            )
            if length_error != "Chapter body is outside the allowed Thai character range":
                break
            count = len(re.sub(r"\s", "", chapter.body))
            try:
                chapter = _request_chapter(
                    plan, selected_context, state, character_context, earlier_context,
                    rewrite_brief=(
                        f"บทมีความยาว {count} ตัวอักษรไม่รวมช่องว่าง "
                        "กรุณาเขียนใหม่ให้อยู่ระหว่าง 2,400 ถึง 7,200 ตัวอักษร "
                        "โดยคงเหตุการณ์และ canon เดิมทั้งหมด"
                    ), draft=chapter
                )
            except Exception:
                break
            print(f"[Historian] Chapter length retry {attempt + 1}/2")
        error, critique = _validate_and_critique(
            chapter, plan, state, previous_body, selected_logs
        )
        if error:
            return {"error": error}
        if critique and not critique.approved:
            chapter = _request_chapter(
                plan,
                selected_context,
                state,
                character_context,
                earlier_context,
                rewrite_brief=critique.rewrite_brief,
                draft=chapter,
            )
            error, final_critique = _validate_and_critique(
                chapter, plan, state, previous_body, selected_logs
            )
            if error:
                return {"error": error}
            if final_critique and not final_critique.approved:
                return {"error": "Critique rejected rewritten chapter"}

        last_log = selected_logs[-1]
        next_state = _advance_story_state(state, selected_logs)
        db.save_chapter(
            target_round,
            chapter.title,
            chapter.body,
            last_log["location"],
            last_log["p1_name"],
            last_log["p2_name"],
            chapter.tone,
            story_state=next_state,
        )
        saved_chapter = db.get_chapter_by_round(target_round)
        export_chapter(saved_chapter)
        export_all_characters()
        rebuild_index(db.list_chapters())

        return {
            "title": chapter.title,
            "novel": chapter.body,
            "round_num": target_round,
        }
    except (ValidationError, ValueError) as error:
        return {"error": f"Historian returned invalid structured data: {error}"}
    except Exception as error:
        return {"error": str(error)}
