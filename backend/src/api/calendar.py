"""Calendar API endpoints."""

import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..storage import StorageBackend
from ..templates.daily_note import render_daily_note

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


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend from app state."""
    return request.app.state.storage


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

    # Get all daily note paths for this month
    daily_notes_prefix = f"Daily-Notes/{year}-{month_str}"
    try:
        all_files = await storage.list(daily_notes_prefix)
        existing_notes = {
            f.split("/")[-1].replace(".md", "")
            for f in all_files
            if f.endswith(".md")
        }
    except Exception:
        existing_notes = set()

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

    # Build the path
    path = f"Daily-Notes/{year}-{month}/{request.date}.md"

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
    content = await _render_from_vault_template(storage, request.date)
    if content is None:
        content = render_daily_note(request.date)

    # Write the new note
    await storage.write(path, content.encode("utf-8"))

    return DailyNoteResponse(path=path, created=True, content=content)


async def _render_from_vault_template(storage: StorageBackend, date_str: str) -> str | None:
    """Try to render a daily note from the vault template.

    Reads Templates/daily.md, wraps it with frontmatter and nav links.
    Returns None if the vault template doesn't exist.
    """
    try:
        template_bytes = await storage.read("Templates/daily.md")
        template_body = template_bytes.decode("utf-8")
    except (FileNotFoundError, Exception):
        logger.debug("Vault template not found, using hardcoded template")
        return None

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

    return f"""\
---
date: {date_str}
type: daily-note
tags:
  - daily
  - journal
---

{template_body}
---
**Previous**: [[{prev_date}]] | **Next**: [[{next_date}]]
"""


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
                r"- \*\*Type\*\*:.*\n- \*\*Focus\*\*:.*",
                "- Rest day",
                result,
            )
        else:
            result = re.sub(r"^(- \*\*Type\*\*:)\s*$", rf"\1 {workout}", result, flags=re.MULTILINE)
            result = re.sub(r"^(- \*\*Focus\*\*:)\s*$", rf"\1 {workout}", result, flags=re.MULTILINE)

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
