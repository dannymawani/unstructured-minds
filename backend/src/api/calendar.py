"""Calendar API endpoints."""

import logging
from calendar import monthrange
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..storage import StorageBackend
from .dependencies import get_db as _dep_get_db, get_storage as _dep_get_storage
from ..templates.daily_note import render_daily_note as render_fallback_template

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/calendar", tags=["calendar"])


class DayInfo(BaseModel):
    """Information about a single day."""

    day: int
    date: str
    has_note: bool
    activity_level: int  # 0-3 based on content/extractions


class MonthDataResponse(BaseModel):
    """Response for month data endpoint."""

    year: int
    month: int
    days: list[DayInfo]


def get_db(request: Request):
    """Get database manager from app state."""
    return _dep_get_db(request)


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend (user-scoped in cloud mode)."""
    return _dep_get_storage(request)


def get_claude(request: Request) -> ClaudeClient:
    """Get Claude client from app state."""
    return request.app.state.claude


@router.get("/month", response_model=MonthDataResponse)
async def get_month_data(
    year: int = Query(..., ge=1900, le=2100, description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> MonthDataResponse:
    """Get data about each day in the specified month.

    Returns information about whether a daily note exists and
    the activity level (based on extractions/content) for each day.

    Args:
        year: Year to query
        month: Month to query (1-12)
        db: Database manager
        storage: Storage backend

    Returns:
        Month data with information about each day
    """
    # Get the number of days in the month
    _, num_days = monthrange(year, month)

    # Format month with leading zero
    month_str = str(month).zfill(2)

    # Get all daily note paths for this month via directory listing
    import re as _re
    from .settings import resolve_daily_note_path, get_daily_note_template
    existing_notes: set[str] = set()
    try:
        # Derive the month directory from the template for a fast directory listing
        sample_path = resolve_daily_note_path(f"{year}-{month_str}-01")
        month_prefix = "/".join(sample_path.split("/")[:-1])
        all_files = await storage.list(month_prefix)
        for f in all_files:
            if not f.endswith(".md"):
                continue
            fname = f.split("/")[-1].removesuffix(".md").removesuffix("-daily-note")
            if _re.match(r"\d{4}-\d{2}-\d{2}$", fname):
                existing_notes.add(fname)
    except Exception:
        pass

    # Get activity counts from database for the month
    # Count extractions per day
    start_date = f"{year}-{month_str}-01"
    end_date = f"{year}-{month_str}-{num_days:02d}"

    # Query activities count per day
    activity_counts: dict[str, int] = {}
    try:
        result = db.execute(
            """
            SELECT date, COUNT(*) as count
            FROM activities
            WHERE date >= ? AND date <= ?
            GROUP BY date
            """,
            [start_date, end_date],
        ).fetchall()
        for row in result:
            activity_counts[str(row[0])] = row[1]
    except Exception:
        pass

    # Query exercise count per day
    exercise_counts: dict[str, int] = {}
    try:
        result = db.execute(
            """
            SELECT date, COUNT(*) as count
            FROM exercise_log
            WHERE date >= ? AND date <= ?
            GROUP BY date
            """,
            [start_date, end_date],
        ).fetchall()
        for row in result:
            exercise_counts[str(row[0])] = row[1]
    except Exception:
        pass

    # Build day info for each day of the month
    days: list[DayInfo] = []
    for day in range(1, num_days + 1):
        day_str = f"{day:02d}"
        date_str = f"{year}-{month_str}-{day_str}"

        # Check if daily note exists
        has_note = date_str in existing_notes

        # Calculate activity level (0-3)
        total_activity = activity_counts.get(date_str, 0) + exercise_counts.get(date_str, 0)
        if total_activity == 0:
            activity_level = 0
        elif total_activity <= 2:
            activity_level = 1
        elif total_activity <= 5:
            activity_level = 2
        else:
            activity_level = 3

        days.append(
            DayInfo(
                day=day,
                date=date_str,
                has_note=has_note,
                activity_level=activity_level,
            )
        )

    return MonthDataResponse(
        year=year,
        month=month,
        days=days,
    )


class DailyNoteRequest(BaseModel):
    """Request to create a daily note."""

    date: str  # YYYY-MM-DD format


class DailyNoteResponse(BaseModel):
    """Response for daily note creation."""

    path: str
    created: bool
    content: str


@router.post("/daily-note", response_model=DailyNoteResponse)
async def create_or_get_daily_note(
    request: DailyNoteRequest,
    storage: StorageBackend = Depends(get_storage),
) -> DailyNoteResponse:
    """Create or retrieve a daily note.

    If the note already exists, returns its content.
    If it doesn't exist, creates it from a template.

    Args:
        request: Date for the daily note
        storage: Storage backend

    Returns:
        Daily note path, creation status, and content
    """
    # Parse the date
    try:
        year, month, day = request.date.split("-")
        date_obj = date(int(year), int(month), int(day))
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Build the path using configurable template
    from .settings import resolve_daily_note_path
    path = resolve_daily_note_path(request.date)

    # Check if the note already exists
    try:
        exists = await storage.exists(path)
    except Exception:
        exists = False

    if exists:
        # Read existing content
        content_bytes = await storage.read(path)
        content = content_bytes.decode("utf-8")
        return DailyNoteResponse(path=path, created=False, content=content)

    # Try reading vault template first, fall back to hardcoded
    content = await _render_from_vault_template(storage)
    if content is None:
        content = render_fallback_template()

    # Write the new note
    await storage.write(path, content.encode("utf-8"))

    return DailyNoteResponse(path=path, created=True, content=content)


async def _render_from_vault_template(storage: StorageBackend) -> str | None:
    """Try to read the daily note template from the vault.

    Reads Templates/daily.md and returns its content as-is.
    Returns None if the vault template doesn't exist.
    """
    try:
        template_bytes = await storage.read("Templates/daily.md")
        return template_bytes.decode("utf-8")
    except (FileNotFoundError, Exception):
        logger.debug("Vault template not found, using hardcoded template")
        return None


class WorkoutSuggestionExercise(BaseModel):
    """Single exercise in a workout suggestion."""

    exercise_name: str
    display_name: str = ""
    sets: int = 0
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    suggested_weight_kg: Optional[float] = None


class WorkoutSuggestionData(BaseModel):
    """Workout suggestion from last strength session."""

    date: Optional[str] = None
    exercises: list[WorkoutSuggestionExercise] = []
    focus: Optional[str] = None


class RolloverTaskForPopulate(BaseModel):
    """A rolled-over task to include in the daily note."""

    description: str
    deadline: Optional[str] = None
    deadline_status: Optional[str] = None  # "overdue" | "due_today" | "upcoming" | None


class PopulateDailyNoteRequest(BaseModel):
    """Request to populate a daily note template with wizard answers."""

    date: str
    template: str
    workout: Optional[str] = None
    sleep: Optional[int] = None
    energy: Optional[int] = None
    mood: Optional[int] = None
    work_priorities: Optional[str] = None
    personal: Optional[str] = None
    adhoc: Optional[str] = None
    workout_suggestion: Optional[WorkoutSuggestionData] = None
    rollover_tasks: Optional[list[RolloverTaskForPopulate]] = None


class PopulateDailyNoteResponse(BaseModel):
    """Response for daily note population."""

    content: str
    used_ai: bool


@router.post("/daily-note/populate", response_model=PopulateDailyNoteResponse)
async def populate_daily_note(
    request: PopulateDailyNoteRequest,
    claude: ClaudeClient = Depends(get_claude),
) -> PopulateDailyNoteResponse:
    """Populate a daily note template with wizard answers using AI.

    Falls back to simple string replacement if Claude is not configured.
    """
    answers = {
        "workout": request.workout,
        "sleep": request.sleep,
        "energy": request.energy,
        "mood": request.mood,
        "work_priorities": request.work_priorities or "",
        "personal": request.personal or "",
        "adhoc": request.adhoc or "",
        "workout_suggestion": request.workout_suggestion.model_dump() if request.workout_suggestion else None,
        "rollover_tasks": [t.model_dump() for t in request.rollover_tasks] if request.rollover_tasks else None,
    }

    if claude.is_configured:
        try:
            content = await claude.populate_daily_note(
                template=request.template,
                answers=answers,
                date=request.date,
            )
            return PopulateDailyNoteResponse(content=content, used_ai=True)
        except Exception as e:
            logger.warning("AI populate failed, falling back to string replacement: %s", e)

    # Fallback: simple string replacement
    content = _populate_fallback(request.template, answers)
    return PopulateDailyNoteResponse(content=content, used_ai=False)


def _populate_fallback(template: str, answers: dict) -> str:
    """Simple string replacement fallback when AI is unavailable."""
    import re

    result = template

    # Workout
    workout = answers.get("workout")
    if workout:
        if workout == "Rest":
            result = re.sub(
                r"[*-] \*\*Type\*\*:.*\n[*-] \*\*Focus\*\*:.*",
                "- Rest day",
                result,
            )
        else:
            result = re.sub(r"^([*-] \*\*Type\*\*:)\s*$", rf"\1 {workout}", result, flags=re.MULTILINE)
            result = re.sub(r"^([*-] \*\*Focus\*\*:)\s*$", rf"\1 {workout}", result, flags=re.MULTILINE)

    # Workout suggestion — insert table after Focus line
    suggestion = answers.get("workout_suggestion")
    if suggestion and suggestion.get("exercises"):
        date_str = suggestion.get("date", "")
        table_lines = [
            "",
            f"> **Suggested Workout (from {date_str})** — edit below to log, or delete if skipping",
            "> ",
            "> | Exercise | Last | Suggested | Reps | Sets |",
            "> |----------|------|-----------|------|------|",
        ]
        for ex in suggestion["exercises"]:
            name = ex.get("display_name") or ex.get("exercise_name", "")
            last_w = f"{ex['weight_kg']}kg" if ex.get("weight_kg") and ex["weight_kg"] > 0 else "BW"
            sugg_w = f"{ex['suggested_weight_kg']}kg" if ex.get("suggested_weight_kg") else last_w
            reps = str(ex.get("reps")) if ex.get("reps") else "-"
            sets = str(ex.get("sets")) if ex.get("sets") else "-"
            table_lines.append(f"> | {name} | {last_w} | {sugg_w} | {reps} | {sets} |")
        table_lines.append("")
        suggestion_block = "\n".join(table_lines)

        focus_match = re.search(r"^[*-] \*\*Focus\*\*:.*$", result, re.MULTILINE)
        if focus_match:
            insert_pos = focus_match.end()
            result = result[:insert_pos] + "\n" + suggestion_block + result[insert_pos:]

    # Carried Forward tasks — insert before Today's Focus
    rollover_tasks = answers.get("rollover_tasks")
    if rollover_tasks:
        lines = ["## Carried Forward\n"]
        for task in rollover_tasks:
            desc = task["description"]
            dl_status = task.get("deadline_status")
            deadline = task.get("deadline")
            if dl_status == "overdue" and deadline:
                # Format deadline date nicely
                try:
                    from datetime import date as _date
                    dl = _date.fromisoformat(deadline)
                    formatted = dl.strftime("%b %d").replace(" 0", " ")
                    desc += f" (Overdue: {formatted})"
                except ValueError:
                    desc += f" (Overdue: {deadline})"
            elif dl_status == "due_today":
                desc += " (Due today)"
            elif dl_status == "upcoming" and deadline:
                try:
                    from datetime import date as _date
                    dl = _date.fromisoformat(deadline)
                    formatted = dl.strftime("%b %d").replace(" 0", " ")
                    desc += f" ({formatted})"
                except ValueError:
                    desc += f" ({deadline})"
            lines.append(f"- [ ] {desc}")
        carried_block = "\n".join(lines) + "\n\n"

        focus_idx = result.find("## 🎯 Today's Focus")
        if focus_idx != -1:
            result = result[:focus_idx] + carried_block + result[focus_idx:]
        else:
            # Insert before first ## section if no Today's Focus found
            first_section = re.search(r"^## ", result, re.MULTILINE)
            if first_section:
                result = result[:first_section.start()] + carried_block + result[first_section.start():]
            else:
                result = result + "\n" + carried_block

    # Metrics
    sleep = answers.get("sleep")
    if sleep:
        result = re.sub(r"^(- Sleep:)\s*$", rf"\1 {sleep}/10", result, flags=re.MULTILINE)
    energy = answers.get("energy")
    if energy:
        result = re.sub(r"^(- Energy Level:)\s*$", rf"\1 {energy}/10", result, flags=re.MULTILINE)
    mood = answers.get("mood")
    if mood:
        result = re.sub(r"^(- Mood:)\s*$", rf"\1 {mood}/10", result, flags=re.MULTILINE)

    # Work priorities -> checkboxes under ## 💼 Work
    work = answers.get("work_priorities", "")
    if work.strip():
        items = [line.strip() for line in work.replace(",", "\n").split("\n") if line.strip()]
        checkboxes = "\n".join(f"- [ ] {item}" for item in items)
        result = result.replace("## 💼 Work\n\n", f"## 💼 Work\n{checkboxes}\n\n")

        # Also populate Today's Focus with top items
        focus_items = items[:4]
        focus_checkboxes = "\n".join(f"- [ ] {item}" for item in focus_items)
        result = re.sub(
            r"## 🎯 Today's Focus\n\n- \[ \]\n\n- \[ \]",
            f"## 🎯 Today's Focus\n\n{focus_checkboxes}",
            result,
        )

    # Personal -> checkboxes under ## 🤷🏽 Personal
    personal = answers.get("personal", "")
    if personal.strip():
        items = [line.strip() for line in personal.replace(",", "\n").split("\n") if line.strip()]
        checkboxes = "\n".join(f"- [ ] {item}" for item in items)
        result = result.replace("## 🤷🏽 Personal\n\n", f"## 🤷🏽 Personal\n{checkboxes}\n\n")

    # Adhoc -> bullets under ## 📝 Adhoc Notes
    adhoc = answers.get("adhoc", "")
    if adhoc.strip():
        items = [line.strip() for line in adhoc.split("\n") if line.strip()]
        bullets = "\n".join(f"- {item}" for item in items)
        result = result.replace("## 📝 Adhoc Notes\n-\n", f"## 📝 Adhoc Notes\n{bullets}\n")

    return result
