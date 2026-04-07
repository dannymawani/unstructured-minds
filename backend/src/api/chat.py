"""Unified chat endpoint - handles data queries, note updates, and multi-day catchup."""

import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..claude import ClaudeClient
from ..cache import invalidate_all
from ..middleware import limiter
from ..middleware.rate_limit import RATE_LIMIT_CLAUDE_API
from ..middleware.validation import MAX_QUERY_LENGTH
from ..storage import StorageBackend
from ..templates.daily_note import render_daily_note as render_fallback_template
from .dependencies import get_storage as _dep_get_storage, get_user_id
from .settings import resolve_daily_note_path

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

UNIFIED_CHAT_SYSTEM_PROMPT = """You are the assistant for Unstructured Minds, a personal journaling app. You help the user in three ways:

1. **Catch up on missed days**: When the user describes activities across multiple days (e.g., "Monday I did BJJ, Tuesday was rest day"), use the create_daily_notes tool. Parse natural language into structured per-day data. Today is {today} ({today_weekday}).

   Date inference rules:
   - "today" = {today} (ALWAYS use this exact date for "today")
   - "yesterday" = {yesterday}
   - "Monday" / "Tuesday" etc. = the MOST RECENT past occurrence of that weekday (never future). Compute from today's date {today} ({today_weekday}), NOT relative to other days in the same message.
   - "last Monday" = explicitly the previous week's Monday
   - "3 days ago" = compute from today
   - If the user lists activities without dates, ask which dates they belong to
   - IMPORTANT: Each day reference is computed independently from today. Do NOT chain days sequentially.

   For each day, extract whatever is mentioned:
   - workout: the type (BJJ, Strength, Cardio, Rest, Cycling, etc.)
   - workout_details: the FULL exercise log formatted as markdown. For strength training, format each exercise as:
     ```
     - Exercise Name: sets x reps @ weight
     ```
     For example: "- Deadlift: 1x8 @ 50kg, 1x8 @ 80kg, 1x8 @ 100kg, 1x5 @ 110kg"
     For cardio: "- Bike: 15km in 40 minutes"
     For BJJ: "- BJJ: rolling/drilling" or whatever details given.
     ALWAYS include workout_details when the user provides specific exercises, weights, reps, distances, or durations.
   - sleep/energy/mood: 1-10 rating if mentioned
   - work: work items, projects, meetings
   - personal: personal tasks, errands, appointments
   - adhoc: random notes, thoughts
   Only include fields the user actually mentioned. Don't invent data.

2. **Query data**: When the user asks questions about their personal data (sleep patterns, workout history, nutrition, tasks, etc.), use the query_data tool. Pass the user's question as-is.

3. **Update the current note**: When the user has a note open and asks you to add, change, or remove something, return the full updated note content wrapped in <note-update>...</note-update> tags. Outside the tags, give a brief reply explaining what you changed.

   Note section mapping:
   - Tasks/to-dos -> ## 🎯 Today's Focus (use `- [ ] description` checkbox format)
   - Quick notes, captures -> ## 📝 Adhoc Notes (use `- item` format)
   - Work items, meetings -> ## 💼 Work
   - Personal items, errands -> ## 🤷🏽 Personal
   - Workouts -> ## 🏋️ Training & Health > ### Workout
   - Sleep/energy/mood -> ## 🏋️ Training & Health > ### Energy & Recovery

   Rules for note updates:
   - Preserve ALL existing content and formatting
   - Add new content in the appropriate section
   - Follow the existing markdown style
   - If the relevant section doesn't exist, create it in a logical position

If the user is just chatting or you can't determine the intent, respond conversationally.
Keep replies concise and friendly."""


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

CREATE_DAILY_NOTES_TOOL = {
    "name": "create_daily_notes",
    "description": "Create or update daily journal notes for multiple days. Use when the user is catching up on days they missed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "notes": {
                "type": "array",
                "description": "One entry per day to log",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format",
                        },
                        "workout": {
                            "type": "string",
                            "description": "Workout type (e.g. 'Strength', 'BJJ', 'Cardio', 'Cycling', 'Rest')",
                        },
                        "workout_details": {
                            "type": "string",
                            "description": "Full exercise log as markdown lines. E.g. '- Deadlift: 1x8 @ 50kg, 1x8 @ 80kg\\n- Bench Press: 3x8 @ 65kg' or '- Bike: 15km in 40min'",
                        },
                        "sleep": {
                            "type": "integer",
                            "description": "Sleep quality 1-10",
                        },
                        "energy": {
                            "type": "integer",
                            "description": "Energy level 1-10",
                        },
                        "mood": {
                            "type": "integer",
                            "description": "Mood rating 1-10",
                        },
                        "work": {
                            "type": "string",
                            "description": "Work activities, projects, meetings",
                        },
                        "personal": {
                            "type": "string",
                            "description": "Personal tasks, errands, appointments",
                        },
                        "adhoc": {
                            "type": "string",
                            "description": "Random notes, thoughts, things to remember",
                        },
                    },
                    "required": ["date"],
                },
            },
        },
        "required": ["notes"],
    },
}

QUERY_DATA_TOOL = {
    "name": "query_data",
    "description": "Query the user's personal data (sleep, workouts, nutrition, tasks, etc.). Use when the user asks analytical questions about their data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The data question to answer",
            },
        },
        "required": ["question"],
    },
}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ImageData(BaseModel):
    data: str
    media_type: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    file_path: Optional[str] = None
    file_content: Optional[str] = Field(default=None, max_length=MAX_QUERY_LENGTH * 10)
    images: Optional[list[ImageData]] = Field(default=None, max_length=5)


class CreatedNote(BaseModel):
    date: str
    path: str
    created: bool  # True = new file, False = updated existing


class QueryData(BaseModel):
    columns: list[str]
    data: list[dict[str, Any]]
    sql: Optional[str] = None
    row_count: int = 0


class ChatMessageResponse(BaseModel):
    reply: str
    note_update: Optional[str] = None
    created_notes: Optional[list[CreatedNote]] = None
    query_data: Optional[QueryData] = None


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def get_claude(request: Request) -> ClaudeClient:
    return request.app.state.claude


def get_storage(request: Request) -> StorageBackend:
    return _dep_get_storage(request)


def get_analytics_db(request: Request):
    return request.app.state.analytics_db


# ---------------------------------------------------------------------------
# Catchup logic
# ---------------------------------------------------------------------------

async def _get_template(storage: StorageBackend) -> str:
    try:
        tpl = await storage.read("Templates/daily.md")
        return tpl.decode("utf-8")
    except Exception:
        return render_fallback_template()


def _populate_new_note(template: str, data: dict) -> str:
    """Fill an empty template with catchup data."""
    content = template

    # Workout
    workout = data.get("workout")
    workout_details = data.get("workout_details")
    if workout:
        if workout.lower() == "rest":
            content = re.sub(
                r"(### Workout\n)- \*\*Type\*\*:.*\n- \*\*Focus\*\*:.*",
                r"\g<1>- Rest day",
                content,
            )
        else:
            content = re.sub(r"- \*\*Type\*\*:.*", f"- **Type**: {workout}", content)
            if " - " in workout:
                wtype, wfocus = workout.split(" - ", 1)
                content = re.sub(r"- \*\*Type\*\*:.*", f"- **Type**: {wtype}", content)
                content = re.sub(r"- \*\*Focus\*\*:.*", f"- **Focus**: {wfocus}", content)

    # Insert workout details after Focus line
    if workout_details:
        # Ensure details start with newline-separated bullet points
        details = workout_details.strip()
        m = re.search(r"(- \*\*Focus\*\*:.*\n)", content)
        if m:
            content = content[: m.end()] + "\n" + details + "\n" + content[m.end() :]
        elif re.search(r"- Rest day\n", content):
            pass  # don't add details to rest days
        else:
            # Fallback: insert after ### Workout header
            m2 = re.search(r"(### Workout\n)", content)
            if m2:
                content = content[: m2.end()] + details + "\n" + content[m2.end() :]

    # Energy & Recovery
    for key, label in [("sleep", "Sleep"), ("energy", "Energy Level"), ("mood", "Mood")]:
        val = data.get(key)
        if val is not None:
            content = re.sub(rf"- {label}:.*", f"- {label}: {val}/10", content)

    # Section helpers
    def _items(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"[,\n]", text) if s.strip()]

    # Work
    work = data.get("work")
    if work:
        md = "\n".join(f"- [ ] {i}" for i in _items(work))
        content = re.sub(r"(## 💼 Work\n)\s*\n", f"\\g<1>{md}\n\n", content)

    # Personal
    personal = data.get("personal")
    if personal:
        md = "\n".join(f"- [ ] {i}" for i in _items(personal))
        content = re.sub(r"(## 🤷🏽 Personal\n)\s*\n", f"\\g<1>{md}\n\n", content)

    # Adhoc
    adhoc = data.get("adhoc")
    if adhoc:
        md = "\n".join(f"- {i}" for i in _items(adhoc))
        content = re.sub(r"(## 📝 Adhoc Notes\n)-\s*$", f"\\g<1>{md}", content, flags=re.MULTILINE)

    # Today's Focus — top items from work + personal
    focus = []
    if work:
        focus.extend(_items(work)[:2])
    if personal:
        focus.extend(_items(personal)[:2])
    if focus:
        focus_md = "\n\n".join(f"- [ ] {i}" for i in focus[:4])
        content = re.sub(
            r"(## 🎯 Today's Focus\n)\s*- \[ \]\s*\n\s*- \[ \]\s*",
            f"\\g<1>{focus_md}\n",
            content,
        )

    return content


def _merge_into_existing(content: str, data: dict) -> str:
    """Append catchup data into sections of an existing note (won't overwrite filled fields)."""
    workout = data.get("workout")
    workout_details = data.get("workout_details")
    if workout and re.search(r"- \*\*Type\*\*:\s*$", content, re.MULTILINE):
        if workout.lower() == "rest":
            content = re.sub(
                r"(### Workout\n)- \*\*Type\*\*:\s*\n- \*\*Focus\*\*:\s*",
                r"\g<1>- Rest day",
                content,
            )
        else:
            content = re.sub(
                r"- \*\*Type\*\*:\s*$", f"- **Type**: {workout}", content, flags=re.MULTILINE,
            )

    # Insert workout details
    if workout_details:
        details = workout_details.strip()
        m = re.search(r"(- \*\*Focus\*\*:.*\n)", content)
        if m:
            content = content[: m.end()] + "\n" + details + "\n" + content[m.end() :]
        else:
            m2 = re.search(r"(### Workout\n)", content)
            if m2:
                content = content[: m2.end()] + details + "\n" + content[m2.end() :]

    for key, label in [("sleep", "Sleep"), ("energy", "Energy Level"), ("mood", "Mood")]:
        val = data.get(key)
        if val is not None and re.search(rf"- {label}:\s*$", content, re.MULTILINE):
            content = re.sub(rf"- {label}:\s*$", f"- {label}: {val}/10", content, flags=re.MULTILINE)

    def _items(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"[,\n]", text) if s.strip()]

    for section_key, header in [("work", "## 💼 Work"), ("personal", "## 🤷🏽 Personal")]:
        text = data.get(section_key)
        if text:
            md = "\n".join(f"- [ ] {i}" for i in _items(text))
            m = re.search(re.escape(header) + r"\n", content)
            if m:
                content = content[: m.end()] + md + "\n" + content[m.end() :]

    adhoc = data.get("adhoc")
    if adhoc:
        md = "\n".join(f"- {i}" for i in _items(adhoc))
        m = re.search(r"## .*Adhoc Notes\n", content)
        if m:
            content = content[: m.end()] + md + "\n" + content[m.end() :]

    return content


_STRENGTH_PATTERN = re.compile(r"\d+x\d+\s*@\s*\d+\s*kg", re.IGNORECASE)
_STRENGTH_TYPES = {"strength", "gym", "weights", "lifting", "weightlifting"}


def _sanitize_catchup_entry(entry: dict) -> dict:
    """Ensure workout_details match the workout type.

    Prevents the LLM from copying strength-training details into BJJ/cardio/rest
    days when it hallucinates during multi-day catchup.
    """
    workout = (entry.get("workout") or "").strip().lower()
    details = entry.get("workout_details") or ""

    # If workout type is not strength-related but details contain strength
    # patterns (sets x reps @ weight), the LLM likely copied from another day.
    if workout and workout not in _STRENGTH_TYPES and _STRENGTH_PATTERN.search(details):
        logger.info(
            "catchup_stripped_mismatched_details",
            date=entry.get("date"),
            workout=workout,
            reason="strength details on non-strength day",
        )
        entry = {**entry, "workout_details": None}

    return entry


async def _handle_catchup(
    notes_data: list[dict],
    storage: StorageBackend,
    request: Request,
    user_id: str,
) -> list[CreatedNote]:
    template = await _get_template(storage)
    results: list[CreatedNote] = []

    # Deduplicate: if the LLM copied identical workout_details across days,
    # only keep them for the first occurrence.
    seen_details: set[str] = set()
    for entry in notes_data:
        details = (entry.get("workout_details") or "").strip()
        if details:
            if details in seen_details:
                logger.info(
                    "catchup_stripped_duplicate_details",
                    date=entry.get("date"),
                    reason="identical details already used for another day",
                )
                entry["workout_details"] = None
            else:
                seen_details.add(details)

    for entry in notes_data:
        entry = _sanitize_catchup_entry(entry)
        date_str = entry.get("date", "")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning("catchup_invalid_date", date=date_str)
            continue

        path = resolve_daily_note_path(date_str)

        try:
            exists = await storage.exists(path)
        except Exception:
            exists = False

        if exists:
            raw = await storage.read(path)
            note_content = _merge_into_existing(raw.decode("utf-8"), entry)
            is_new = False
        else:
            note_content = _populate_new_note(template, entry)
            is_new = True

        await storage.write(path, note_content.encode("utf-8"))
        results.append(CreatedNote(date=date_str, path=path, created=is_new))

        # Run extraction (best effort)
        db = request.app.state.db
        try:
            claude_client: ClaudeClient = request.app.state.claude
            if claude_client.is_configured:
                from ..extraction import ExtractionPipeline

                pipeline = ExtractionPipeline(db, claude_client, user_id=user_id)
                await pipeline.extract(path, note_content)
        except Exception:
            logger.debug("catchup_extraction_failed", path=path, exc_info=True)

        # Ensure a daily_metrics row exists so the dashboard sees this date
        try:
            from ..db.sql_compat import get_dialect

            dialect = get_dialect(db)
            ph = "%s" if dialect == "postgres" else "?"
            if dialect == "postgres":
                sql = (
                    f"INSERT INTO daily_metrics (date, source_file, user_id) "
                    f"VALUES ({ph}, {ph}, {ph}) "
                    f"ON CONFLICT (date, user_id) DO NOTHING"
                )
                db.execute(sql, [date_str, path, user_id])
            else:
                sql = (
                    f"INSERT INTO daily_metrics (date, source_file) "
                    f"SELECT {ph}, {ph} WHERE NOT EXISTS "
                    f"(SELECT 1 FROM daily_metrics WHERE date = {ph})"
                )
                db.execute(sql, [date_str, path, date_str])
        except Exception:
            logger.debug("catchup_metrics_ensure_failed", date=date_str, exc_info=True)

    invalidate_all()
    return results


# ---------------------------------------------------------------------------
# Query logic (reuses query module internals)
# ---------------------------------------------------------------------------

async def _handle_query(question: str, request: Request) -> tuple[Optional[QueryData], str]:
    """Run the query pipeline. Returns (query_data, answer_text)."""
    from .query import (
        SQL_GENERATION_SYSTEM_PROMPT,
        RESPONSE_FORMATTING_SYSTEM_PROMPT,
        validate_sql,
        extract_sql_from_response,
    )

    claude: ClaudeClient = request.app.state.claude
    db = get_analytics_db(request)

    # Generate SQL
    sql_resp = await claude.complete(
        model=claude.model_fast,
        max_tokens=1024,
        system=SQL_GENERATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    raw_sql = sql_resp.text.strip()

    if raw_sql.startswith("INVALID_QUERY"):
        return None, "I can only answer questions about your personal data (sleep, exercise, nutrition, activities, and tasks)."

    sql = extract_sql_from_response(raw_sql)
    if not validate_sql(sql):
        return None, "I had trouble generating a safe query for that question. Could you rephrase?"

    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"SELECT * FROM ({sql}) AS _limited LIMIT 100"

    try:
        result = db.read_only_execute(sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchall()

        data = []
        for row in rows[:100]:
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                if hasattr(val, "isoformat"):
                    val = val.isoformat()
                elif isinstance(val, (bytes, bytearray)):
                    val = val.decode("utf-8", errors="replace")
                row_dict[col] = val
            data.append(row_dict)

        qd = QueryData(columns=columns, data=data, sql=sql, row_count=len(rows))
    except Exception as exc:
        return None, f"I had trouble running that query: {exc}"

    # Format answer
    if not data:
        answer = "No data found matching your question."
    else:
        results_json = json.dumps(data[:20], indent=2, default=str)
        fmt = await claude.complete(
            model=claude.model_fast,
            max_tokens=1024,
            system=RESPONSE_FORMATTING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Question: {question}\n\nQuery results:\n{results_json}"}],
        )
        answer = fmt.text

    return qd, answer


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/chat/message", response_model=ChatMessageResponse)
@limiter.limit(RATE_LIMIT_CLAUDE_API)
async def unified_chat(
    request: Request,
    body: ChatMessageRequest,
    claude: ClaudeClient = Depends(get_claude),
    storage: StorageBackend = Depends(get_storage),
    user_id: str = Depends(get_user_id),
) -> ChatMessageResponse:
    """Unified chat: data queries, note updates, and multi-day catchup in one endpoint."""
    if not claude.is_configured:
        raise HTTPException(503, "LLM not configured. Set LLM_API_KEY or ANTHROPIC_API_KEY.")

    today = date.today()
    yesterday = today - timedelta(days=1)

    system = UNIFIED_CHAT_SYSTEM_PROMPT.format(
        today=today.isoformat(),
        today_weekday=today.strftime("%A"),
        yesterday=yesterday.isoformat(),
    )

    # Build multimodal content (OpenAI format for LiteLLM)
    parts: list[dict[str, Any]] = []
    if body.images:
        for img in body.images:
            parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img.media_type};base64,{img.data}",
                },
            })

    text_pieces = []
    if body.file_path:
        text_pieces.append(f"Currently open file: {body.file_path}")
    if body.file_content:
        text_pieces.append(f"Current note content:\n```markdown\n{body.file_content}\n```")
    text_pieces.append(f"User: {body.message}")
    parts.append({"type": "text", "text": "\n\n".join(text_pieces)})

    # Single LLM call with tools
    response = await claude.complete(
        model=claude.model_smart,
        max_tokens=8192,
        system=system,
        tools=[CREATE_DAILY_NOTES_TOOL, QUERY_DATA_TOOL],
        messages=[{"role": "user", "content": parts}],
    )

    # Parse response (OpenAI format via LiteLLM)
    reply_text = ""
    note_update = None
    created_notes = None
    query_data = None

    # Handle text content
    if response.text:
        text = response.text
        m = re.search(r"<note-update>(.*?)</note-update>", text, re.DOTALL)
        if m:
            note_update = m.group(1).strip()
            text = re.sub(r"<note-update>.*?</note-update>", "", text, flags=re.DOTALL).strip()
        reply_text += text

    # Handle tool calls
    for tc in response.tool_calls:
        args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
        if tc.function.name == "create_daily_notes":
            created_notes = await _handle_catchup(
                args["notes"], storage, request, user_id,
            )
            if not reply_text.strip():
                new_ct = sum(1 for n in created_notes if n.created)
                upd_ct = len(created_notes) - new_ct
                dates = [n.date for n in created_notes]
                bits = []
                if new_ct:
                    bits.append(f"Created {new_ct} new note{'s' if new_ct != 1 else ''}")
                if upd_ct:
                    bits.append(f"updated {upd_ct} existing note{'s' if upd_ct != 1 else ''}")
                reply_text = f"{' and '.join(bits)} for {', '.join(dates)}."

        elif tc.function.name == "query_data":
            query_data, answer = await _handle_query(args["question"], request)
            if not reply_text.strip():
                reply_text = answer

    if not reply_text.strip():
        reply_text = "I'm here to help! You can ask about your data, update your current note, or catch up on missed days."

    # If the note was updated, also persist it
    if note_update and body.file_path:
        try:
            await storage.write(body.file_path, note_update.encode("utf-8"))
            invalidate_all()
        except Exception:
            logger.debug("chat_note_write_failed", path=body.file_path, exc_info=True)

    return ChatMessageResponse(
        reply=reply_text,
        note_update=note_update,
        created_notes=created_notes,
        query_data=query_data,
    )
