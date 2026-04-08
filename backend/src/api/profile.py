"""Life Profile API endpoints."""

import json
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..db.sql_compat import get_dialect, placeholder, user_filter
from ..db.user_settings import UserSettingsStore
from ..storage.datastore import DataStore
from .dependencies import get_datastore as _dep_get_datastore
from .dependencies import get_user_id

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/profile", tags=["profile"])

PROFILE_PATH = "life_profile.json"
PROFILE_FILE = settings.data_path / "life_profile.json"


# --- Pydantic Models ---


class Overview(BaseModel):
    name: str = ""
    age: int | None = None
    location: str = ""
    company: str = ""
    role: str = ""
    summary: str = ""


class PersonalSection(BaseModel):
    family: list[str] = Field(default_factory=list)
    friends: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    notes: str = ""


class WorkSection(BaseModel):
    role: str = ""
    company: str = ""
    projects: list[str] = Field(default_factory=list)
    colleagues: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    notes: str = ""


class TrainingSection(BaseModel):
    disciplines: list[str] = Field(default_factory=list)
    current_lifts: dict[str, str] = Field(default_factory=dict)
    recovery: str = ""
    goals: list[str] = Field(default_factory=list)
    notes: str = ""


class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: str = ""
    description: str = ""
    status: str = "active"
    target_date: str | None = None
    progress: int | None = None


class LifeProfile(BaseModel):
    overview: Overview = Field(default_factory=Overview)
    personal: PersonalSection = Field(default_factory=PersonalSection)
    work: WorkSection = Field(default_factory=WorkSection)
    training: TrainingSection = Field(default_factory=TrainingSection)
    goals: list[Goal] = Field(default_factory=list)


class ReviewCreateRequest(BaseModel):
    period_start: str
    period_end: str
    key_wins: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    work_highlights: str = ""
    training_summary: str = ""
    personal_wins: list[str] = Field(default_factory=list)
    health_metrics: dict | None = None
    goal_progress: dict | None = None
    focus_next: list[str] = Field(default_factory=list)


class ReviewUpdateRequest(BaseModel):
    period_start: str | None = None
    period_end: str | None = None
    key_wins: list[str] | None = None
    challenges: list[str] | None = None
    work_highlights: str | None = None
    training_summary: str | None = None
    personal_wins: list[str] | None = None
    health_metrics: dict | None = None
    goal_progress: dict | None = None
    focus_next: list[str] | None = None


class ReviewOut(BaseModel):
    id: str
    period_start: str
    period_end: str
    key_wins: list[str]
    challenges: list[str]
    work_highlights: str
    training_summary: str
    personal_wins: list[str]
    health_metrics: dict | None
    goal_progress: dict | None
    focus_next: list[str]
    created_at: str
    updated_at: str


# --- Profile helpers ---


def _load_profile_sync() -> dict:
    """Load profile from JSON file (sync fallback for non-request contexts)."""
    if PROFILE_FILE.exists():
        try:
            with open(PROFILE_FILE) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return LifeProfile().model_dump()


def _get_user_settings_store(request: Request, user_id: str):
    """Get UserSettingsStore if running in cloud mode, else None."""
    db = request.app.state.db
    if get_dialect(db) == "postgres":
        return UserSettingsStore(db, user_id)
    return None


async def _load_profile(datastore: DataStore, request: Request = None, user_id: str = None) -> dict:
    """Load profile from Postgres (cloud) or DataStore (local)."""
    if request and user_id:
        store = _get_user_settings_store(request, user_id)
        if store:
            data = store.get("life_profile")
            if data is not None:
                return data
            return LifeProfile().model_dump()

    data = await datastore.read_json(PROFILE_PATH)
    if data is not None:
        return data
    return LifeProfile().model_dump()


async def _save_profile(datastore: DataStore, data: dict, request: Request = None, user_id: str = None) -> None:
    """Save profile to Postgres (cloud) or DataStore (local)."""
    if request and user_id:
        store = _get_user_settings_store(request, user_id)
        if store:
            store.set("life_profile", data)
            return

    await datastore.write_json(PROFILE_PATH, data)


# --- Profile Endpoints ---


@router.get("")
async def get_profile(request: Request, user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> dict:
    """Get full life profile."""
    return await _load_profile(datastore, request, user_id)


@router.put("")
async def update_profile(profile: LifeProfile, request: Request, user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> dict:
    """Update full life profile."""
    data = profile.model_dump()
    await _save_profile(datastore, data, request, user_id)
    return data


@router.patch("/{section}")
async def update_section(section: str, request: Request, request_body: Any = Body(...), user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> dict:
    """Update a single profile section."""
    valid_sections = {"overview", "personal", "work", "training", "goals"}
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section: {section}. Must be one of: {', '.join(sorted(valid_sections))}",
        )

    profile = await _load_profile(datastore, request, user_id)
    profile[section] = request_body
    await _save_profile(datastore, profile, request, user_id)
    return profile


# --- Review Endpoints ---


def _row_to_review(row: tuple, columns: list[str]) -> dict:
    """Convert a DuckDB row to a review dict."""
    d = dict(zip(columns, row))
    # Convert date/timestamp objects to strings
    for key in ("period_start", "period_end"):
        if isinstance(d.get(key), date):
            d[key] = d[key].isoformat()
    for key in ("created_at", "updated_at"):
        if isinstance(d.get(key), datetime):
            d[key] = d[key].isoformat()
    # Ensure list fields are never None
    for key in ("key_wins", "challenges", "personal_wins", "focus_next"):
        if d.get(key) is None:
            d[key] = []
    # Ensure text fields are never None
    for key in ("work_highlights", "training_summary"):
        if d.get(key) is None:
            d[key] = ""
    return d


@router.get("/reviews")
def list_reviews(request: Request, user_id: str = Depends(get_user_id)) -> list[dict]:
    """List all progress reviews, newest first."""
    db = request.app.state.db
    dialect = get_dialect(db)
    conditions: list[str] = []
    params: list = []
    user_filter(dialect, user_id, conditions, params)
    where = f"WHERE {' AND '.join(conditions)} " if conditions else ""
    result = db.execute(
        f"SELECT * FROM progress_reviews {where}ORDER BY period_start DESC",
        params,
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    return [_row_to_review(row, columns) for row in rows]


@router.post("/reviews", status_code=201)
def create_review(review: ReviewCreateRequest, request: Request, user_id: str = Depends(get_user_id)) -> dict:
    """Create a new progress review."""
    db = request.app.state.db
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    review_id = str(uuid.uuid4())[:8]

    cols = ["id", "period_start", "period_end", "key_wins", "challenges",
            "work_highlights", "training_summary", "personal_wins",
            "health_metrics", "goal_progress", "focus_next"]
    vals = [
        review_id,
        review.period_start,
        review.period_end,
        review.key_wins,
        review.challenges,
        review.work_highlights,
        review.training_summary,
        review.personal_wins,
        json.dumps(review.health_metrics) if review.health_metrics else None,
        json.dumps(review.goal_progress) if review.goal_progress else None,
        review.focus_next,
    ]
    if dialect == "postgres":
        cols.append("user_id")
        vals.append(user_id)

    placeholders = ", ".join([ph] * len(cols))
    col_list = ", ".join(cols)
    db.execute(f"INSERT INTO progress_reviews ({col_list}) VALUES ({placeholders})", vals)

    # Fetch the created review
    conditions: list[str] = [f"id = {ph}"]
    params: list = [review_id]
    user_filter(dialect, user_id, conditions, params)
    result = db.execute(
        f"SELECT * FROM progress_reviews WHERE {' AND '.join(conditions)}",
        params,
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_review(row, columns)


@router.get("/reviews/{review_id}")
def get_review(review_id: str, request: Request, user_id: str = Depends(get_user_id)) -> dict:
    """Get a single progress review by ID."""
    db = request.app.state.db
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions: list[str] = [f"id = {ph}"]
    params: list = [review_id]
    user_filter(dialect, user_id, conditions, params)
    result = db.execute(
        f"SELECT * FROM progress_reviews WHERE {' AND '.join(conditions)}",
        params,
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    return _row_to_review(row, columns)


@router.put("/reviews/{review_id}")
def update_review(
    review_id: str, review: ReviewUpdateRequest, request: Request, user_id: str = Depends(get_user_id)
) -> dict:
    """Update an existing progress review."""
    db = request.app.state.db
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    # Check exists
    conditions: list[str] = [f"id = {ph}"]
    params_check: list = [review_id]
    user_filter(dialect, user_id, conditions, params_check)
    existing = db.execute(
        f"SELECT id FROM progress_reviews WHERE {' AND '.join(conditions)}",
        params_check,
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")

    # Build dynamic update
    updates = []
    params: list = []
    for field, value in review.model_dump(exclude_unset=True).items():
        if field in ("health_metrics", "goal_progress") and value is not None:
            updates.append(f"{field} = {ph}")
            params.append(json.dumps(value))
        else:
            updates.append(f"{field} = {ph}")
            params.append(value)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        where_conds: list[str] = [f"id = {ph}"]
        params.append(review_id)
        user_filter(dialect, user_id, where_conds, params)
        db.execute(
            f"UPDATE progress_reviews SET {', '.join(updates)} WHERE {' AND '.join(where_conds)}",
            params,
        )

    # Fetch updated review
    fetch_conds: list[str] = [f"id = {ph}"]
    fetch_params: list = [review_id]
    user_filter(dialect, user_id, fetch_conds, fetch_params)
    result = db.execute(
        f"SELECT * FROM progress_reviews WHERE {' AND '.join(fetch_conds)}",
        fetch_params,
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_review(row, columns)


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: str, request: Request, user_id: str = Depends(get_user_id)) -> None:
    """Delete a progress review."""
    db = request.app.state.db
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    conditions: list[str] = [f"id = {ph}"]
    params: list = [review_id]
    user_filter(dialect, user_id, conditions, params)
    existing = db.execute(
        f"SELECT id FROM progress_reviews WHERE {' AND '.join(conditions)}",
        params,
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")

    db.execute(
        f"DELETE FROM progress_reviews WHERE {' AND '.join(conditions)}",
        params,
    )


# --- Review Generation ---


REVIEW_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "key_wins": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-5 key accomplishments from the period",
        },
        "challenges": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-3 challenges faced during the period",
        },
        "work_highlights": {
            "type": "string",
            "description": "Summary paragraph of work accomplishments",
        },
        "training_summary": {
            "type": "string",
            "description": "Summary paragraph of training and exercise activity",
        },
        "personal_wins": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-3 personal wins or positive life events",
        },
        "health_metrics": {
            "type": "object",
            "properties": {
                "avg_sleep": {"type": "number", "description": "Average sleep quality (1-10)"},
                "avg_energy": {"type": "number", "description": "Average energy level (1-10)"},
                "avg_mood": {"type": "number", "description": "Average mood (1-10)"},
                "avg_stress": {"type": "number", "description": "Average stress level (1-10)"},
            },
            "description": "Averaged health metrics for the period",
        },
        "focus_next": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-4 focus areas for the next period",
        },
    },
    "required": [
        "key_wins",
        "challenges",
        "work_highlights",
        "training_summary",
        "personal_wins",
        "health_metrics",
        "focus_next",
    ],
}


def _gather_review_context(
    db: Any,
    period_start: date,
    period_end: date,
) -> str:
    """Query DuckDB for data in the review period and build a context string.

    Args:
        db: DatabaseManager instance
        period_start: Start of review period
        period_end: End of review period

    Returns:
        Formatted context string for Claude
    """
    sections: list[str] = []
    sections.append(f"Review period: {period_start.isoformat()} to {period_end.isoformat()}")

    # --- Activities ---
    try:
        activities = db.execute(
            """
            SELECT activity_type, COUNT(*) as cnt,
                   COALESCE(SUM(duration_minutes), 0) as total_minutes
            FROM activities
            WHERE date BETWEEN ? AND ?
            GROUP BY activity_type
            ORDER BY cnt DESC
            """,
            [period_start, period_end],
        ).fetchall()
        if activities:
            total_sessions = sum(row[1] for row in activities)
            lines = [f"Total sessions: {total_sessions}"]
            for row in activities:
                lines.append(f"  - {row[0]}: {row[1]} sessions, {row[2]} minutes total")
            sections.append("ACTIVITIES:\n" + "\n".join(lines))
        else:
            sections.append("ACTIVITIES: No activities recorded in this period.")
    except Exception as e:
        logger.warning("Failed to query activities for review: %s", e)
        sections.append("ACTIVITIES: Unable to query.")

    # --- Exercise highlights ---
    try:
        exercises = db.execute(
            """
            SELECT exercise_name,
                   COUNT(*) as total_sets,
                   MAX(weight_kg) as max_weight,
                   MAX(reps) as max_reps
            FROM exercise_log
            WHERE date BETWEEN ? AND ?
            GROUP BY exercise_name
            ORDER BY total_sets DESC
            LIMIT 10
            """,
            [period_start, period_end],
        ).fetchall()
        if exercises:
            lines = []
            for row in exercises:
                name, sets, max_w, max_r = row
                parts = [f"{name}: {sets} sets"]
                if max_w:
                    parts.append(f"max weight {max_w}kg")
                if max_r:
                    parts.append(f"max reps {max_r}")
                lines.append("  - " + ", ".join(parts))
            sections.append("EXERCISE HIGHLIGHTS (top exercises by volume):\n" + "\n".join(lines))
        else:
            sections.append("EXERCISE HIGHLIGHTS: No exercises logged in this period.")
    except Exception as e:
        logger.warning("Failed to query exercises for review: %s", e)
        sections.append("EXERCISE HIGHLIGHTS: Unable to query.")

    # --- Daily metrics averages ---
    try:
        metrics = db.execute(
            """
            SELECT
                ROUND(AVG(sleep_quality), 1) as avg_sleep,
                ROUND(AVG(energy), 1) as avg_energy,
                ROUND(AVG(mood), 1) as avg_mood,
                ROUND(AVG(stress), 1) as avg_stress,
                COUNT(*) as days_tracked
            FROM daily_metrics
            WHERE date BETWEEN ? AND ?
            """,
            [period_start, period_end],
        ).fetchone()
        if metrics and metrics[4] > 0:
            sections.append(
                f"DAILY METRICS (averaged over {metrics[4]} days):\n"
                f"  - Avg sleep quality: {metrics[0]}/10\n"
                f"  - Avg energy: {metrics[1]}/10\n"
                f"  - Avg mood: {metrics[2]}/10\n"
                f"  - Avg stress: {metrics[3]}/10"
            )
        else:
            sections.append("DAILY METRICS: No metrics recorded in this period.")
    except Exception as e:
        logger.warning("Failed to query daily metrics for review: %s", e)
        sections.append("DAILY METRICS: Unable to query.")

    # --- Completed tasks ---
    try:
        tasks = db.execute(
            """
            SELECT category, COUNT(*) as cnt
            FROM tasks
            WHERE date BETWEEN ? AND ?
              AND status = 'done'
            GROUP BY category
            ORDER BY cnt DESC
            """,
            [period_start, period_end],
        ).fetchall()
        total_done = sum(row[1] for row in tasks) if tasks else 0

        total_tasks = db.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE date BETWEEN ? AND ?
            """,
            [period_start, period_end],
        ).fetchone()
        total_all = total_tasks[0] if total_tasks else 0

        if total_done > 0:
            lines = [f"Completed {total_done} of {total_all} tasks"]
            for row in tasks:
                cat = row[0] or "uncategorized"
                lines.append(f"  - {cat}: {row[1]} completed")
            sections.append("TASKS:\n" + "\n".join(lines))
        else:
            sections.append(f"TASKS: {total_all} tasks recorded, none marked as done.")
    except Exception as e:
        logger.warning("Failed to query tasks for review: %s", e)
        sections.append("TASKS: Unable to query.")

    # --- Recent task descriptions for richer context ---
    try:
        recent_tasks = db.execute(
            """
            SELECT description, status, category
            FROM tasks
            WHERE date BETWEEN ? AND ?
              AND status = 'done'
            ORDER BY date DESC
            LIMIT 20
            """,
            [period_start, period_end],
        ).fetchall()
        if recent_tasks:
            lines = [f"  - {row[0]} [{row[2] or 'general'}]" for row in recent_tasks]
            sections.append("RECENTLY COMPLETED TASKS:\n" + "\n".join(lines))
    except Exception:
        pass  # Non-critical

    return "\n\n".join(sections)


@router.post("/reviews/generate")
async def generate_review(request: Request, user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> dict:
    """Auto-generate a progress review using AI based on data since the last review.

    Queries activities, exercises, daily metrics, and tasks from DuckDB,
    sends the context to Claude, and returns generated review data.
    The review is NOT saved -- the user can edit before saving.

    Returns:
        Generated review data matching ReviewCreateRequest schema.
    """
    db = request.app.state.db
    claude = request.app.state.claude

    if not claude.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Claude API is not configured. Set ANTHROPIC_API_KEY to enable AI features.",
        )

    # Determine review period
    today = date.today()
    dialect = get_dialect(db)
    try:
        conditions: list[str] = []
        params: list = []
        user_filter(dialect, user_id, conditions, params)
        where = f"WHERE {' AND '.join(conditions)} " if conditions else ""
        last_review = db.execute(
            f"SELECT period_end FROM progress_reviews {where}ORDER BY period_end DESC LIMIT 1",
            params,
        ).fetchone()
    except Exception:
        last_review = None

    if last_review and last_review[0]:
        last_end = last_review[0]
        if isinstance(last_end, str):
            last_end = date.fromisoformat(last_end)
        period_start = last_end + timedelta(days=1)
    else:
        period_start = today - timedelta(days=30)

    period_end = today

    # Don't generate a review for a nonsensical period
    if period_start > period_end:
        raise HTTPException(
            status_code=400,
            detail=f"No new period to review. Last review ended {period_start - timedelta(days=1)}, which is today or in the future.",
        )

    logger.info(
        "Generating review for period %s to %s",
        period_start.isoformat(),
        period_end.isoformat(),
    )

    # Gather data context from DuckDB
    context = _gather_review_context(db, period_start, period_end)

    # Load life profile for additional context
    profile = await _load_profile(datastore, request, user_id)
    profile_summary = ""
    if profile.get("overview", {}).get("name"):
        profile_summary = f"User: {profile['overview']['name']}"
        if profile["overview"].get("role"):
            profile_summary += f", {profile['overview']['role']}"
        if profile["overview"].get("company"):
            profile_summary += f" at {profile['overview']['company']}"

    full_context = (
        f"Generate a progress review for the following period.\n"
        f"{profile_summary}\n\n"
        f"{context}\n\n"
        f"Based on this data, generate a thoughtful progress review. "
        f"If data is sparse, still provide reasonable observations and focus areas. "
        f"Be specific and reference actual data points where possible. "
        f"Keep summaries concise but insightful."
    )

    try:
        result = await claude.extract(full_context, REVIEW_EXTRACTION_SCHEMA)
    except Exception as e:
        logger.error("Claude extraction failed for review generation: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Failed to generate review with AI. Please try again or write manually.",
        )

    # Build the response with period dates and generated content
    generated = {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "key_wins": result.get("key_wins", []),
        "challenges": result.get("challenges", []),
        "work_highlights": result.get("work_highlights", ""),
        "training_summary": result.get("training_summary", ""),
        "personal_wins": result.get("personal_wins", []),
        "health_metrics": result.get("health_metrics"),
        "goal_progress": None,
        "focus_next": result.get("focus_next", []),
    }

    logger.info(
        "Review generated successfully: %d wins, %d challenges, %d focus areas",
        len(generated["key_wins"]),
        len(generated["challenges"]),
        len(generated["focus_next"]),
    )

    return generated
