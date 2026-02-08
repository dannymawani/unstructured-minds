"""Dashboard API endpoints."""

import uuid
from datetime import date, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..db import DatabaseManager


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


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


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
    last_note_row = db.execute(
        """
        SELECT file_path FROM extraction_log
        WHERE file_path LIKE '%Daily-Notes%' AND success = TRUE
        ORDER BY file_path DESC
        LIMIT 1
        """
    ).fetchone()
    last_daily_note = None
    if last_note_row and last_note_row[0]:
        last_daily_note = last_note_row[0].split('/')[-1].removesuffix('.md')

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
    db: DatabaseManager = Depends(get_db),
) -> ExerciseTableResponse:
    """Get a summary table of strength exercises the user has logged.

    Filtered to strength-related exercises only (by activity_id or manual entries).
    Returns one row per exercise with last trained date, recent weight,
    best weight, and total sessions.

    Args:
        search: Optional search filter for exercise names
        limit: Number of exercises to return (default 10)
        offset: Pagination offset
        db: Database manager

    Returns:
        Table of exercise summaries sorted by total sessions descending
    """
    where_clauses = ["(activity_id LIKE '%strength%' OR source_file = 'manual_entry')"]
    params: list[Any] = []

    if search:
        where_clauses.append("exercise_name ILIKE ?")
        params.append(f"%{search}%")

    where_sql = " AND ".join(where_clauses)

    # Get total count
    count_result = db.execute(
        f"""
        SELECT COUNT(DISTINCT exercise_name) FROM exercise_log
        WHERE {where_sql}
        """,
        params,
    ).fetchone()
    total_count = count_result[0] if count_result else 0

    result = db.execute(
        f"""
        WITH filtered AS (
            SELECT * FROM exercise_log
            WHERE {where_sql}
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
        ORDER BY es.total_sessions DESC, ls.last_trained_date DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()

    exercises = [
        ExerciseTableEntry(
            exercise_name=row[0],
            last_trained_date=str(row[1]),
            last_weight_kg=float(row[2]) if row[2] is not None else None,
            max_weight_kg=float(row[3]) if row[3] is not None else None,
            total_sessions=row[4],
        )
        for row in result
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
            exercise.exercise_name,
            exercise.weight_kg,
            exercise.reps,
            exercise.set_number,
            exercise.notes,
        ],
    )

    return ExerciseCreateResponse(
        id=exercise_id,
        message=f"Exercise '{exercise.exercise_name}' added successfully",
    )


class LastWorkoutExercise(BaseModel):
    """Single exercise from the last workout."""

    exercise_name: str
    sets: int
    reps: Optional[int] = None
    weight_kg: Optional[float] = None


class LastWorkoutResponse(BaseModel):
    """Response for last strength workout endpoint."""

    date: Optional[str] = None
    exercises: list[LastWorkoutExercise]
    focus: Optional[str] = None


@router.get("/last-strength-workout", response_model=LastWorkoutResponse)
def get_last_strength_workout(
    db: DatabaseManager = Depends(get_db),
) -> LastWorkoutResponse:
    """Get the last strength training workout to suggest a template.

    Returns exercises from the most recent strength session so the user
    can use them as a starting point for their next workout.

    Args:
        db: Database manager

    Returns:
        Last workout date, exercises, and focus area
    """
    # Find the most recent strength activity date
    last_date_row = db.execute(
        """
        SELECT MAX(date) FROM activities
        WHERE activity_type = 'strength'
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

    exercises = [
        LastWorkoutExercise(
            exercise_name=row[0],
            sets=row[1],
            reps=int(row[2]) if row[2] is not None else None,
            weight_kg=float(row[3]) if row[3] is not None else None,
        )
        for row in exercise_rows
    ]

    return LastWorkoutResponse(
        date=last_date,
        exercises=exercises,
        focus=focus,
    )
