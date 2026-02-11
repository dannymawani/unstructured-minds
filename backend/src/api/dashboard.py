"""Dashboard API endpoints."""

import uuid
from datetime import date, timedelta
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..db import DatabaseManager
from ..extraction.exercise_matcher import ExerciseMatcher
from ..extraction.exercise_normalizer import normalize_exercises
from .dependencies import get_db as _get_db, get_analytics_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class Period(BaseModel):
    """Time period for dashboard queries."""

    start_date: str
    end_date: str
    days: int


class ActivitySummary(BaseModel):
    """Summary of activities by type."""

    activity_type: str
    count: int
    total_duration_minutes: int


class WeeklyActivityResponse(BaseModel):
    """Response for weekly activity endpoint."""

    activities: list[ActivitySummary]
    total_duration_minutes: int
    period: Period


class MetricEntry(BaseModel):
    """Single day of metrics."""

    date: str
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None
    energy: Optional[int] = None
    mood: Optional[int] = None
    stress: Optional[int] = None


class MetricsTrendsResponse(BaseModel):
    """Response for metrics trends endpoint."""

    metrics: list[MetricEntry]
    period: Period


class ExerciseProgressEntry(BaseModel):
    """Single day of exercise progress."""

    date: str
    max_weight_kg: Optional[float] = None
    total_reps: int
    total_sets: int


class ExerciseSummary(BaseModel):
    """Summary statistics for an exercise."""

    current_max: Optional[float] = None
    all_time_max: Optional[float] = None
    total_volume: int
    total_sessions: int


class ExerciseProgressResponse(BaseModel):
    """Response for exercise progress endpoint."""

    exercise: str
    progress: list[ExerciseProgressEntry]
    summary: ExerciseSummary
    period: Period


class DashboardSummaryResponse(BaseModel):
    """Response for dashboard summary endpoint."""

    total_activities: int
    total_exercises: int
    total_daily_notes: int
    streak_days: int
    last_activity_date: Optional[str] = None
    last_daily_note_date: Optional[str] = None
    period: Period


class HeatmapDay(BaseModel):
    """Single day data for heatmap."""

    date: str
    count: int
    duration_minutes: int


class HeatmapResponse(BaseModel):
    """Response for heatmap endpoint."""

    days: list[HeatmapDay]
    year: int
    max_count: int
    max_duration: int


class CorrelationEntry(BaseModel):
    """Single day of correlation data."""

    date: str
    sleep_hours: Optional[float] = None
    energy: Optional[int] = None
    mood: Optional[int] = None
    stress: Optional[int] = None
    activity_minutes: Optional[int] = None


class Correlations(BaseModel):
    """Correlation coefficients between metrics."""

    sleep_mood: Optional[float] = None
    sleep_energy: Optional[float] = None
    activity_mood: Optional[float] = None
    activity_energy: Optional[float] = None
    stress_mood: Optional[float] = None


class CorrelationResponse(BaseModel):
    """Response for correlation endpoint."""

    entries: list[CorrelationEntry]
    correlations: Correlations


class ExerciseTableEntry(BaseModel):
    """Single exercise row in the exercise table."""

    exercise_name: str
    last_trained_date: str
    last_weight_kg: Optional[float] = None
    max_weight_kg: Optional[float] = None
    total_sessions: int


class ExerciseTableResponse(BaseModel):
    """Response for exercise table endpoint."""

    exercises: list[ExerciseTableEntry]
    total_count: int
    offset: int
    limit: int


class ExerciseCreate(BaseModel):
    """Request model for manually adding an exercise."""

    date: date
    exercise_name: str = Field(..., min_length=1, max_length=200)
    weight_kg: Optional[float] = None
    reps: Optional[int] = None
    set_number: int = 1
    notes: Optional[str] = None


class ExerciseCreateResponse(BaseModel):
    """Response for exercise creation."""

    id: str
    message: str
    is_new: bool = False
    canonical_name: str | None = None


def get_db(request: Request):
    """Get analytics database for dashboard reads."""
    return get_analytics_db(request)


def get_exercise_matcher(request: Request) -> ExerciseMatcher:
    """Get exercise matcher from app state."""
    return request.app.state.exercise_matcher


def get_period(days: int) -> Period:
    """Calculate period from days."""
    end = date.today()
    start = end - timedelta(days=days - 1)
    return Period(
        start_date=str(start),
        end_date=str(end),
        days=days,
    )


def calculate_correlation(x: list[float], y: list[float]) -> Optional[float]:
    """Calculate Pearson correlation coefficient between two lists.

    Returns None if there's insufficient data or no variance.
    """
    if len(x) < 3 or len(y) < 3 or len(x) != len(y):
        return None

    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi ** 2 for xi in x)
    sum_y2 = sum(yi ** 2 for yi in y)

    # Calculate denominator
    denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5

    if denominator == 0:
        return None

    # Calculate correlation
    correlation = (n * sum_xy - sum_x * sum_y) / denominator
    return round(correlation, 3)


@router.get("/weekly-activity", response_model=WeeklyActivityResponse)
def get_weekly_activity(
    days: int = Query(default=7, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> WeeklyActivityResponse:
    """Get activity summary for the specified period.

    Args:
        days: Number of days to include (default 7)
        db: Database manager

    Returns:
        Activity summary grouped by type
    """
    period = get_period(days)

    result = db.execute(
        """
        SELECT
            activity_type,
            COUNT(*) as count,
            COALESCE(SUM(duration_minutes), 0) as total_duration
        FROM activities
        WHERE date >= ? AND date <= ?
        GROUP BY activity_type
        ORDER BY total_duration DESC
        """,
        [period.start_date, period.end_date],
    ).fetchall()

    activities = [
        ActivitySummary(
            activity_type=row[0],
            count=row[1],
            total_duration_minutes=int(row[2]),
        )
        for row in result
    ]

    total_duration = sum(a.total_duration_minutes for a in activities)

    return WeeklyActivityResponse(
        activities=activities,
        total_duration_minutes=total_duration,
        period=period,
    )


@router.get("/metrics-trends", response_model=MetricsTrendsResponse)
def get_metrics_trends(
    days: int = Query(default=7, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> MetricsTrendsResponse:
    """Get daily metrics trends for the specified period.

    Args:
        days: Number of days to include (default 7)
        db: Database manager

    Returns:
        Daily metrics sorted by date
    """
    period = get_period(days)

    result = db.execute(
        """
        SELECT
            date,
            sleep_hours,
            sleep_quality,
            energy,
            mood,
            stress
        FROM daily_metrics
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
        """,
        [period.start_date, period.end_date],
    ).fetchall()

    metrics = [
        MetricEntry(
            date=str(row[0]),
            sleep_hours=float(row[1]) if row[1] is not None else None,
            sleep_quality=row[2],
            energy=row[3],
            mood=row[4],
            stress=row[5],
        )
        for row in result
    ]

    return MetricsTrendsResponse(
        metrics=metrics,
        period=period,
    )


@router.get("/exercise-progress", response_model=ExerciseProgressResponse)
def get_exercise_progress(
    exercise: str = Query(..., description="Exercise name to track"),
    days: int = Query(default=30, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> ExerciseProgressResponse:
    """Get progress for a specific exercise.

    Args:
        exercise: Exercise name
        days: Number of days to include (default 30)
        db: Database manager

    Returns:
        Exercise progress with daily max and summary stats
    """
    period = get_period(days)

    # Get daily progress
    result = db.execute(
        """
        SELECT
            date,
            MAX(weight_kg) as max_weight,
            SUM(reps) as total_reps,
            COUNT(*) as total_sets
        FROM exercise_log
        WHERE exercise_name = ? AND date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date ASC
        """,
        [exercise, period.start_date, period.end_date],
    ).fetchall()

    progress = [
        ExerciseProgressEntry(
            date=str(row[0]),
            max_weight_kg=float(row[1]) if row[1] is not None else None,
            total_reps=row[2] or 0,
            total_sets=row[3] or 0,
        )
        for row in result
    ]

    # Calculate summary
    summary_result = db.execute(
        """
        SELECT
            MAX(weight_kg) as all_time_max,
            SUM(COALESCE(weight_kg, 0) * COALESCE(reps, 0)) as total_volume,
            COUNT(DISTINCT date) as total_sessions
        FROM exercise_log
        WHERE exercise_name = ?
        """,
        [exercise],
    ).fetchone()

    # Get current max (from most recent session)
    current_max_result = db.execute(
        """
        SELECT MAX(weight_kg)
        FROM exercise_log
        WHERE exercise_name = ? AND date = (
            SELECT MAX(date) FROM exercise_log WHERE exercise_name = ?
        )
        """,
        [exercise, exercise],
    ).fetchone()

    summary = ExerciseSummary(
        current_max=float(current_max_result[0]) if current_max_result and current_max_result[0] else None,
        all_time_max=float(summary_result[0]) if summary_result and summary_result[0] else None,
        total_volume=int(summary_result[1]) if summary_result and summary_result[1] else 0,
        total_sessions=summary_result[2] if summary_result else 0,
    )

    return ExerciseProgressResponse(
        exercise=exercise,
        progress=progress,
        summary=summary,
        period=period,
    )


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> DashboardSummaryResponse:
    """Get overall dashboard summary.

    Args:
        days: Number of days to include (default 30)
        db: Database manager

    Returns:
        Dashboard overview with totals and streak
    """
    period = get_period(days)

    def fetch_scalar(result, default=0):
        row = result.fetchone()
        return row[0] if row and row[0] is not None else default

    # Get activity counts
    activity_count = fetch_scalar(db.execute(
        """
        SELECT COUNT(*) FROM activities
        WHERE date >= ? AND date <= ?
        """,
        [period.start_date, period.end_date],
    ))

    # Get exercise counts
    exercise_count = fetch_scalar(db.execute(
        """
        SELECT COUNT(*) FROM exercise_log
        WHERE date >= ? AND date <= ?
        """,
        [period.start_date, period.end_date],
    ))

    # Get daily notes count (distinct dates in daily_metrics within period)
    daily_notes_count = fetch_scalar(db.execute(
        """
        SELECT COUNT(DISTINCT date) FROM daily_metrics
        WHERE date >= ? AND date <= ?
        """,
        [period.start_date, period.end_date],
    ))

    # Get last activity date
    last_activity = fetch_scalar(db.execute(
        "SELECT MAX(date) FROM activities"
    ), default=None)

    # Get last daily note date from extraction_log file paths
    # Match both Daily-Notes/YYYY-MM/YYYY-MM-DD.md and YYYY/MM/YYYY-MM-DD-daily-note.md
    import re as _re
    last_note_row = db.execute(
        """
        SELECT file_path FROM extraction_log
        WHERE success = TRUE
          AND (file_path LIKE '%/____-__-__.md'
               OR file_path LIKE '%/____-__-__-daily-note.md')
        ORDER BY file_path DESC
        LIMIT 1
        """
    ).fetchone()
    last_daily_note = None
    if last_note_row and last_note_row[0]:
        fname = last_note_row[0].split('/')[-1].removesuffix('.md').removesuffix('-daily-note')
        if _re.match(r'\d{4}-\d{2}-\d{2}$', fname):
            last_daily_note = fname

    # Calculate streak (consecutive days with activities ending today or yesterday)
    # Single query: fetch all distinct activity dates in the last year
    activity_dates_result = db.execute(
        """
        SELECT DISTINCT date FROM activities
        WHERE date >= ? AND date <= ?
        ORDER BY date DESC
        """,
        [str(date.today() - timedelta(days=365)), str(date.today())],
    ).fetchall()
    activity_dates = {row[0] for row in activity_dates_result}

    streak = 0
    check_date = date.today()
    if check_date not in activity_dates:
        # Allow starting from yesterday if no activity today yet
        check_date -= timedelta(days=1)
    while check_date in activity_dates and streak <= 365:
        streak += 1
        check_date -= timedelta(days=1)

    return DashboardSummaryResponse(
        total_activities=activity_count,
        total_exercises=exercise_count,
        total_daily_notes=daily_notes_count,
        streak_days=streak,
        last_activity_date=str(last_activity) if last_activity else None,
        last_daily_note_date=str(last_daily_note) if last_daily_note else None,
        period=period,
    )


@router.get("/heatmap", response_model=HeatmapResponse)
def get_heatmap_data(
    year: int = Query(default=None, ge=2020, le=2100, description="Year to show"),
    db: DatabaseManager = Depends(get_db),
) -> HeatmapResponse:
    """Get activity heatmap data for a specific year.

    Returns activity count and duration for each day of the year.

    Args:
        year: Year to get data for (default: current year)
        db: Database manager

    Returns:
        List of days with activity counts and durations
    """
    if year is None:
        year = date.today().year

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    result = db.execute(
        """
        SELECT
            date,
            COUNT(*) as count,
            COALESCE(SUM(duration_minutes), 0) as duration
        FROM activities
        WHERE date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date ASC
        """,
        [start_date, end_date],
    ).fetchall()

    days = [
        HeatmapDay(
            date=str(row[0]),
            count=row[1],
            duration_minutes=int(row[2]),
        )
        for row in result
    ]

    max_count = max((d.count for d in days), default=0)
    max_duration = max((d.duration_minutes for d in days), default=0)

    return HeatmapResponse(
        days=days,
        year=year,
        max_count=max_count,
        max_duration=max_duration,
    )


@router.get("/correlation", response_model=CorrelationResponse)
def get_correlation_data(
    days: int = Query(default=30, ge=7, le=365),
    db: DatabaseManager = Depends(get_db),
) -> CorrelationResponse:
    """Get metric correlation data for analysis.

    Calculates correlations between various metrics to identify patterns.

    Args:
        days: Number of days to include (default 30, minimum 7)
        db: Database manager

    Returns:
        Daily entries and calculated correlation coefficients
    """
    period = get_period(days)

    # Get metrics with activity data joined
    result = db.execute(
        """
        SELECT
            m.date,
            m.sleep_hours,
            m.energy,
            m.mood,
            m.stress,
            COALESCE(a.total_minutes, 0) as activity_minutes
        FROM daily_metrics m
        LEFT JOIN (
            SELECT date, SUM(duration_minutes) as total_minutes
            FROM activities
            GROUP BY date
        ) a ON m.date = a.date
        WHERE m.date >= ? AND m.date <= ?
        ORDER BY m.date ASC
        """,
        [period.start_date, period.end_date],
    ).fetchall()

    entries = [
        CorrelationEntry(
            date=str(row[0]),
            sleep_hours=float(row[1]) if row[1] is not None else None,
            energy=row[2],
            mood=row[3],
            stress=row[4],
            activity_minutes=row[5],
        )
        for row in result
    ]

    # Calculate correlations using entries with complete data
    sleep_values = []
    energy_values = []
    mood_values = []
    stress_values = []
    activity_values = []

    for e in entries:
        if e.sleep_hours is not None and e.energy is not None and e.mood is not None and e.stress is not None:
            sleep_values.append(e.sleep_hours)
            energy_values.append(float(e.energy))
            mood_values.append(float(e.mood))
            stress_values.append(float(e.stress))
            activity_values.append(float(e.activity_minutes or 0))

    correlations = Correlations(
        sleep_mood=calculate_correlation(sleep_values, mood_values),
        sleep_energy=calculate_correlation(sleep_values, energy_values),
        activity_mood=calculate_correlation(activity_values, mood_values),
        activity_energy=calculate_correlation(activity_values, energy_values),
        stress_mood=calculate_correlation(stress_values, mood_values),
    )

    return CorrelationResponse(
        entries=entries,
        correlations=correlations,
    )


@router.get("/exercise-table", response_model=ExerciseTableResponse)
def get_exercise_table(
    search: Optional[str] = Query(default=None, description="Search exercises by name"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["total_sessions", "last_trained_date", "max_weight_kg", "last_weight_kg", "exercise_name"] = Query(
        default="total_sessions", description="Column to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sort direction"),
    db: DatabaseManager = Depends(get_db),
    matcher: ExerciseMatcher = Depends(get_exercise_matcher),
) -> ExerciseTableResponse:
    """Get a summary table of strength exercises the user has logged.

    Filtered to strength-related exercises only (by activity_id or manual entries).
    Exercise names are normalized via fuzzy matching so variants like
    "Deadlift" / "deadlift" / "Deadlifts" merge into one row.

    Args:
        search: Optional search filter for exercise names
        limit: Number of exercises to return (default 10)
        offset: Pagination offset
        db: Database manager

    Returns:
        Table of exercise summaries sorted by total sessions descending
    """
    # Fetch all strength exercises grouped by raw name
    result = db.execute(
        """
        WITH filtered AS (
            SELECT * FROM exercise_log
            WHERE activity_id LIKE '%strength%' OR source_file = 'manual_entry'
        ),
        latest_session AS (
            SELECT
                exercise_name,
                date as last_trained_date,
                weight_kg as last_weight_kg,
                ROW_NUMBER() OVER (
                    PARTITION BY exercise_name
                    ORDER BY date DESC, set_number DESC
                ) as rn
            FROM filtered
        ),
        exercise_stats AS (
            SELECT
                exercise_name,
                MAX(weight_kg) as max_weight_kg,
                COUNT(DISTINCT date) as total_sessions
            FROM filtered
            GROUP BY exercise_name
        )
        SELECT
            es.exercise_name,
            ls.last_trained_date,
            ls.last_weight_kg,
            es.max_weight_kg,
            es.total_sessions
        FROM exercise_stats es
        JOIN latest_session ls
            ON es.exercise_name = ls.exercise_name AND ls.rn = 1
        """,
    ).fetchall()

    # Normalize names and merge duplicates
    merged: dict[str, dict[str, Any]] = {}
    for row in result:
        raw_name = row[0]
        canonical, _ = matcher.match(raw_name)

        if canonical in merged:
            entry = merged[canonical]
            if str(row[1]) > entry["last_trained_date"]:
                entry["last_trained_date"] = str(row[1])
                entry["last_weight_kg"] = float(row[2]) if row[2] is not None else entry["last_weight_kg"]
            if row[3] is not None:
                if entry["max_weight_kg"] is None or float(row[3]) > entry["max_weight_kg"]:
                    entry["max_weight_kg"] = float(row[3])
            entry["total_sessions"] += row[4]
        else:
            merged[canonical] = {
                "exercise_name": canonical,
                "last_trained_date": str(row[1]),
                "last_weight_kg": float(row[2]) if row[2] is not None else None,
                "max_weight_kg": float(row[3]) if row[3] is not None else None,
                "total_sessions": row[4],
            }

    # Filter by search on canonical names
    items = list(merged.values())
    if search:
        search_lower = search.lower()
        items = [e for e in items if search_lower in e["exercise_name"].lower()]

    # Sort by requested column, with last_trained_date as secondary sort
    reverse = sort_order == "desc"
    none_default: Any = "" if sort_by in ("last_trained_date", "exercise_name") else -1
    items.sort(
        key=lambda x: (
            x[sort_by] if x[sort_by] is not None else none_default,
            x["last_trained_date"],
        ),
        reverse=reverse,
    )

    total_count = len(items)
    paginated = items[offset:offset + limit]

    exercises = [
        ExerciseTableEntry(
            exercise_name=e["exercise_name"],
            last_trained_date=e["last_trained_date"],
            last_weight_kg=e["last_weight_kg"],
            max_weight_kg=e["max_weight_kg"],
            total_sessions=e["total_sessions"],
        )
        for e in paginated
    ]

    return ExerciseTableResponse(
        exercises=exercises,
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


@router.post("/exercises", status_code=201, response_model=ExerciseCreateResponse)
def create_exercise(
    exercise: ExerciseCreate,
    db: DatabaseManager = Depends(get_db),
    matcher: ExerciseMatcher = Depends(get_exercise_matcher),
) -> ExerciseCreateResponse:
    """Manually add an exercise entry to the exercise log.

    This allows users to log exercises directly without going through
    the note extraction pipeline.

    Args:
        exercise: Exercise data to insert
        db: Database manager

    Returns:
        Created exercise ID and confirmation message
    """
    exercise_id = str(uuid.uuid4())
    activity_id = f"manual_{exercise.date}_{exercise_id[:8]}"
    canonical_name, confidence = matcher.match(exercise.exercise_name)

    # An exercise is "new" if it didn't match any builtin or community definition
    is_new = confidence == 0.0

    db.execute(
        """
        INSERT INTO exercise_log (
            id, activity_id, date, exercise_name,
            weight_kg, reps, set_number, notes,
            source_file, extracted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'manual_entry', CURRENT_TIMESTAMP)
        """,
        [
            exercise_id,
            activity_id,
            str(exercise.date),
            canonical_name,
            exercise.weight_kg,
            exercise.reps,
            exercise.set_number,
            exercise.notes,
        ],
    )

    return ExerciseCreateResponse(
        id=exercise_id,
        message=f"Exercise '{canonical_name}' added successfully",
        is_new=is_new,
        canonical_name=canonical_name,
    )


class LastWorkoutExercise(BaseModel):
    """Single exercise from the last workout."""

    exercise_name: str
    display_name: str
    sets: int
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    suggested_weight_kg: Optional[float] = None


class LastWorkoutResponse(BaseModel):
    """Response for last strength workout endpoint."""

    date: Optional[str] = None
    exercises: list[LastWorkoutExercise]
    focus: Optional[str] = None


def _load_json_config(filename: str, request: Request = None) -> dict:
    """Load a JSON config file. Checks user_settings (Postgres) first, then data dir."""
    import json

    # In hybrid/postgres mode, check user_settings table
    if request:
        from ..db.sql_compat import get_dialect
        from ..db.user_settings import UserSettingsStore
        db = request.app.state.db
        if get_dialect(db) == "postgres":
            key = filename.removesuffix(".json")
            store = UserSettingsStore(db, settings.default_user_id)
            data = store.get(key)
            if data is not None:
                return data

    config_path = settings.data_path / filename
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


def _format_display_name(name: str) -> str:
    """Convert snake_case to Title Case."""
    return name.replace("_", " ").title()


@router.get("/last-strength-workout", response_model=LastWorkoutResponse)
def get_last_strength_workout(
    request: Request,
    db: DatabaseManager = Depends(get_db),
    matcher: ExerciseMatcher = Depends(get_exercise_matcher),
) -> LastWorkoutResponse:
    """Get the last strength training workout with progressive overload suggestions.

    Returns exercises from the most recent strength session with suggested
    weights (+1.5kg) so the user can plan their next workout.

    Args:
        db: Database manager

    Returns:
        Last workout date, exercises with suggested weights, and focus area
    """
    # Load config for progressive overload increment and exercise display names
    training_config = _load_json_config("training_config.json", request)
    exercise_defs = _load_json_config("exercise_definitions.json")
    increment = training_config.get("preferences", {}).get(
        "progressive_overload_increment_kg", 1.5
    )

    # Find the most recent date with both a strength activity AND logged exercises
    last_date_row = db.execute(
        """
        SELECT MAX(el.date)
        FROM exercise_log el
        INNER JOIN activities a ON el.date = a.date AND a.activity_type = 'strength'
        WHERE el.exercise_name IS NOT NULL
        """
    ).fetchone()

    if not last_date_row or not last_date_row[0]:
        return LastWorkoutResponse(exercises=[])

    last_date = str(last_date_row[0])

    # Get the activity notes (which may contain focus area)
    activity_row = db.execute(
        """
        SELECT notes FROM activities
        WHERE activity_type = 'strength' AND date = ?
        LIMIT 1
        """,
        [last_date],
    ).fetchone()

    focus = activity_row[0] if activity_row and activity_row[0] else None

    # Get exercises from that date
    exercise_rows = db.execute(
        """
        SELECT
            exercise_name,
            COUNT(*) as sets,
            MAX(reps) as reps,
            MAX(weight_kg) as weight_kg
        FROM exercise_log
        WHERE date = ? AND exercise_name IS NOT NULL
        GROUP BY exercise_name
        ORDER BY MIN(set_number)
        """,
        [last_date],
    ).fetchall()

    exercises = []
    for row in exercise_rows:
        name = row[0]
        # Normalize via fuzzy matcher
        canonical, _ = matcher.match(name)
        weight = float(row[3]) if row[3] is not None else None
        # Progressive overload: +increment for weighted exercises
        suggested = round(weight + increment, 1) if weight and weight > 0 else None
        # Display name: use canonical name (already the display name from definitions)
        display = canonical

        exercises.append(
            LastWorkoutExercise(
                exercise_name=canonical,
                display_name=display,
                sets=row[1],
                reps=int(row[2]) if row[2] is not None else None,
                weight_kg=weight,
                suggested_weight_kg=suggested,
            )
        )

    return LastWorkoutResponse(
        date=last_date,
        exercises=exercises,
        focus=focus,
    )


class NormalizeExercisesResponse(BaseModel):
    """Response for exercise normalization endpoint."""

    total_names: int
    already_matched: int
    ai_classified: int
    title_cased: int
    errors: list[str]


@router.post("/normalize-exercises", response_model=NormalizeExercisesResponse)
async def trigger_normalize_exercises(
    request: Request,
    db: DatabaseManager = Depends(get_db),
    matcher: ExerciseMatcher = Depends(get_exercise_matcher),
) -> NormalizeExercisesResponse:
    """Manually trigger exercise name normalization.

    Runs the full normalization pipeline: loads AI cache, queries DB,
    matches names, classifies unmatched via Claude, and saves cache.

    Returns:
        Normalization statistics
    """
    claude = request.app.state.claude
    cache_path = settings.data_path / "ai_exercise_cache.json"

    stats = await normalize_exercises(
        db=db,
        matcher=matcher,
        claude=claude,
        cache_path=cache_path,
    )

    return NormalizeExercisesResponse(
        total_names=stats.total_names,
        already_matched=stats.already_matched,
        ai_classified=stats.ai_classified,
        title_cased=stats.title_cased,
        errors=stats.errors or [],
    )
