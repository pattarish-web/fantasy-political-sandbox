import copy
import json
import os
import re

from pydantic import ValidationError

from app import db, narrative
from app.export_html import export_all_characters, export_chapter, rebuild_index
from app.llm_client import call_llm, clean_json_response
from app.schemas import ChapterCritique, ChapterPlan, ChapterResult


MAX_EVENTS_PER_CHAPTER = 3
MAX_REWRITE_ATTEMPTS = 5
ALLOWED_TONES = frozenset({"epic", "dark", "tragic", "mysterious", "romantic", "neutral"})
# gpt-4o-mini occasionally returns a compact but complete Thai scene. Keep a
# meaningful floor without rejecting valid chapters after all length retries.
MIN_BODY_CHARACTERS = 3000
MAX_BODY_CHARACTERS = 7200
PRESENT_ACTION_VERBS = ("ยืน", "เดิน", "กล่าว", "ตอบ", "สั่ง", "ยื่น", "ชัก", "ใช้")
MIN_REUSED_DIALOGUE_LENGTH = 20
MIN_PARAGRAPHS = 6
MAX_PARAGRAPHS = 12
BLOCKING_CRITIQUE_TERMS = ("canon", "continuity", "ต่อเนื่อง", "เหตุและผล", "causality", "resurrection", "ตาย")


def _critique_is_blocking(issues: list[str]) -> bool:
    text = " ".join(issues).lower()
    return any(term.lower() in text for term in BLOCKING_CRITIQUE_TERMS)


def _normalize_plan_tone(plan: ChapterPlan) -> ChapterPlan:
    if plan.tone in ALLOWED_TONES:
        return plan
    print(f"[Historian] Unsupported tone '{plan.tone}', normalized to 'neutral'")
    return plan.model_copy(update={"tone": "neutral"})


def _opening_stage(chapter_count: int) -> str:
    return ("บทนำ: กำเนิดโลกและสงครามเก่า" if chapter_count == 0 else
            "บทที่ 1: ปูโลกและกฎแฟนตาซี" if chapter_count == 1 else
            "บทที่ 2: อธิบายฝ่ายการเมือง" if chapter_count == 2 else
            "บทที่ 3: เปิดตัวละครและปมหลัก" if chapter_count == 3 else
            "เนื้อเรื่องหลัก: ผลกระทบต่อเนื่อง")


def _opening_contract(chapter_count: int) -> str:
    if chapter_count <= 1:
        return """[Opening structure contract]
This is the opening of the reset world. Explain the world's origin, the old war or collapse,
the current political order, and the minimum magic/race rules through concrete scenes.
Do not start with unexplained dialogue. End with a clear pressure that leads forward.
"""
    if chapter_count == 2:
        return """[Political structure contract]
Explain the major factions, their interests, resources, alliances, and costs through conflict.
Do not introduce a new unrelated subplot or skip directly to a battle without stakes.
"""
    if chapter_count == 3:
        return """[Character reveal contract]
Introduce the central characters through choices and consequences, then reveal the main mystery
or conflict. Tie each character to a faction and leave a concrete unresolved question.
"""
    return ""


def _normalize_text(text: str) -> str:
    return " ".join(str(text).split())


def _quoted_lines(text: str) -> set[str]:
    matches = re.findall(r'["“](.{20,}?)[”"]', text, flags=re.DOTALL)
    return {
        normalized
        for match in matches
        if len(normalized := _normalize_text(match)) >= MIN_REUSED_DIALOGUE_LENGTH
    }


def _validate_prose_quality(body: str) -> str | None:
    """Reject drafts whose prose structure is too compressed to edit safely."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    if re.search(r"\b(the|and|but|with|from|because|however)\b", body, flags=re.IGNORECASE):
        return "Chapter contains untranslated English prose"
    if any(_normalize_text(left) == _normalize_text(right) for left, right in zip(paragraphs, paragraphs[1:])):
        return "Chapter repeats an identical paragraph"
    return None


def _validate_opening_prose(body: str, chapter_count: int) -> str | None:
    """Keep the first published chapter from skipping the world introduction."""
    if chapter_count != 0 or os.getenv("ENFORCE_OPENING_CONTRACT") != "1":
        return None
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    if len(paragraphs) < MIN_PARAGRAPHS:
        return "Opening chapter must contain at least six connected paragraphs"
    lower = body.lower()
    world_terms = ("โลก", "สงคราม", "เวท", "เผ่า", "อำนาจ", "อาณาจักร")
    if sum(term in lower for term in world_terms) < 3:
        return "Opening chapter must establish the world, its conflict, and its rules"
    return None


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
    prose_error = _validate_prose_quality(body)
    if prose_error:
        return prose_error
    opening_error = _validate_opening_prose(body, int(state.get("chapter_count", 0)))
    if opening_error:
        return opening_error
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

        emotional = facts.get("emotional_arc")
        if isinstance(emotional, dict):
            recorded = {"round_num": round_num, **copy.deepcopy(emotional)}
            if recorded not in next_state["emotional_arcs"]:
                next_state["emotional_arcs"].append(recorded)

        consequence = str(log.get("consequence", "")).strip()
        if consequence:
            thread = {"round_num": round_num, "status": "open", "consequence": consequence}
            if thread not in next_state["open_threads"]:
                next_state["open_threads"].append(thread)

    next_state["open_threads"] = next_state["open_threads"][-12:]
    next_state["emotional_arcs"] = next_state["emotional_arcs"][-24:]
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
        spawned = log.get("story_facts", {}).get("character_spawned")
        if isinstance(spawned, dict) and spawned.get("name"):
            involved_characters.add(str(spawned["name"]))
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

[Required story stage]
{_opening_stage(int(state.get('chapter_count', 0)))}

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
    rounds = sorted([int(value) for value in re.findall(r"Event \d+ \(Round (\d+)\)", selected_context)])
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
    # World-bible context is always available, so it cannot be used to detect
    # whether this is the opening. The persisted chapter count is authoritative.
    chapter_count = int(state.get("chapter_count", 0))
    opening_contract = _opening_contract(chapter_count)
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
{opening_contract}
{draft_context}
[Authoring contract]
- Write elegant, natural Thai prose in 3,000–7,200 non-whitespace characters.
- Follow the approved plan and its one central conflict exactly.
- Write as an experienced Thai novelist, never as a literal translation from English. Use
  natural Thai word order, varied sentence rhythm, concrete verbs, and natural connective phrases.
- CRITICAL LITERARY RULES (Show, Don't Tell):
  * AVOID repeatedly naming emotions or relying on abstract adjectives. Words like "ความไม่ไว้วางใจ", "ความตึงเครียด", "ความกังวล", "หวาดระแวง", "มืดมน" are heavily restricted; limit their literal use to at most once per chapter.
  * Show character feelings through choices, hesitation, silence, physical detail (e.g. clenching fists, avoiding eye contact, sighing, adjusting grip on a weapon), and subtext.
  * Anchor the scene in the environment. Describe at least one sensory detail of the location (e.g. the chill radiating from the iron walls, the smell of rust and fire, the flickering shadows of torches, or the howling wind outside) to build a rich atmosphere.
- DIALOGUE & SUBTEXT RULES:
  * Dialogue must be natural, sharp, indirect, and layered with political subtext. Characters should not speak like they are reading an official report or declaring their feelings bluntly.
  * Use pauses (Silence/Beat), physical reactions, and subtextual negotiations.
- Use no more than two present-time POV characters.
- Format the body as 6-12 readable paragraphs separated by blank lines. Each paragraph
  must advance action, reveal a concrete detail, or change a relationship; do not repeat
  the same conclusion in different words.
- Every paragraph must connect causally to the previous one through a gesture, decision,
  consequence, change of location, or shift in attention. Build each scene as situation ->
  action/dialogue -> reaction -> consequence, with a clear emotional turn.
- Give every present character a private desire, fear, and immediate emotional reaction.
  End with at least one changed relationship or belief caused by the chapter's events.
- Show the approved choice and its concrete cost through scene, action, and dialogue.
- State the central choice, who is forced to make it, and the immediate political cost
  within the first two paragraphs. Give each named character a distinct speaking style.
- Do not retell resolved events, deaths, or prior dialogue as if they happen now.
- A canon-dead character may appear only as memory or consequence, never as a present-time actor.
- Do not add a death or resurrection outside selected source facts.
- End with the approved specific unresolved consequence.
- Before returning the draft, silently proofread Thai fluency, speaker continuity, repeated
  wording, untranslated English, and abrupt sentence joins.
"""
    payload = _load_payload(call_llm(prompt, response_schema=ChapterResult))
    # Some providers omit the redundant tone field during a rewrite even though
    # the approved plan already fixes it. Preserve the plan's validated tone so
    # a formatting omission cannot abort an otherwise usable draft.
    payload.setdefault("tone", plan.tone)
    return ChapterResult.model_validate(payload)


def _request_critique(
    plan: ChapterPlan,
    chapter: ChapterResult,
    state: dict,
) -> ChapterCritique:
    prompt = f"""
You are a strict Thai fiction editor. Assess this draft against the approved plan and canon.
Block it if continuity, causality, political clarity, character voice, repetition, unnatural
translated Thai, abrupt paragraph joins, or weak emotional progression would harm readers.
Give one short, location-specific rewrite brief. Preserve events, facts, and outcomes; do not
invent a new subplot. Do not rewrite prose yourself.

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
    state = dict(state or {})
    state["chapter_count"] = len(chapters)
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
            if length_error not in (
                "Chapter body is outside the allowed Thai character range",
                "Opening chapter must contain at least six connected paragraphs",
                "Opening chapter must establish the world, its conflict, and its rules",
            ):
                break
            count = len(re.sub(r"\s", "", chapter.body))
            print(f"[Historian] Chapter length retry {attempt + 1}/2")
            try:
                chapter = _request_chapter(
                    plan, selected_context, state, character_context, earlier_context,
                    rewrite_brief=(
                        f"บทมีความยาว {count} ตัวอักษรไม่รวมช่องว่าง "
                        "กรุณาเขียนใหม่ให้อยู่ระหว่าง 3,000 ถึง 7,200 ตัวอักษร "
                        "โดยคงเหตุการณ์และ canon เดิมทั้งหมด"
                        " For an opening-contract failure, rewrite with at least six connected paragraphs that establish the world's origin, current conflict, political order, and magic rules before the first negotiation."
                    ), draft=chapter
                )
            except Exception as e:
                print(f"[Historian] Length retry {attempt + 1} failed: {e}")
                break
        error, critique = _validate_and_critique(
            chapter, plan, state, previous_body, selected_logs
        )
        if error:
            return {"error": error}
        rewrite_attempts = 0
        quality_warning = ""
        while critique and not critique.approved and rewrite_attempts < MAX_REWRITE_ATTEMPTS:
            rewrite_attempts += 1
            issues = "; ".join(critique.blocking_issues) or "ความต่อเนื่องหรือเหตุผลของฉากยังไม่ชัดเจน"
            print(f"[Historian] Critique rejected (rewrite {rewrite_attempts}/{MAX_REWRITE_ATTEMPTS}): {issues}")
            chapter = _request_chapter(
                plan, selected_context, state, character_context, earlier_context,
                rewrite_brief=f"แก้ประเด็นต่อไปนี้อย่างเจาะจง: {issues}\n{critique.rewrite_brief}",
                draft=chapter,
            )
            error, critique = _validate_and_critique(
                chapter, plan, state, previous_body, selected_logs
            )
            if error:
                return {"error": error}
        if critique and not critique.approved:
            issues = "; ".join(critique.blocking_issues) or "ไม่ผ่านการตรวจคุณภาพ"
            if _critique_is_blocking(critique.blocking_issues):
                return {"error": f"Critique rejected after {MAX_REWRITE_ATTEMPTS} rewrites: {issues}"}
            quality_warning = issues

        last_log = selected_logs[-1]
        next_state = _advance_story_state(state, selected_logs)
        db.save_chapter(
            target_round,
            chapter.title,
            chapter.body,
            last_log["location"],
            plan.pov_characters[0] if len(plan.pov_characters) > 0 else last_log["p1_name"],
            plan.pov_characters[1] if len(plan.pov_characters) > 1 else last_log["p2_name"],
            chapter.tone,
            story_state=next_state,
        )
        saved_chapter = db.get_chapter_by_round(target_round)
        if saved_chapter is None:
            return {"error": f"Chapter for round {target_round} was not found after saving"}
        export_chapter(saved_chapter)
        export_all_characters()
        rebuild_index(db.list_chapters())

        result = {
            "title": chapter.title,
            "novel": chapter.body,
            "round_num": target_round,
        }
        if quality_warning:
            result["warning"] = quality_warning
        return result
    except (ValidationError, ValueError) as error:
        return {"error": f"Historian returned invalid structured data: {error}"}
    except Exception as error:
        import traceback
        print(f"[Historian] Unexpected error: {traceback.format_exc()}")
        return {"error": str(error)}
