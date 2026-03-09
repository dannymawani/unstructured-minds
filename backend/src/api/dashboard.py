"""Dashboard API endpoints."""

import uuid
from datetime import date, timedelta
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..db import DatabaseManager
from ..extraction.exercise_matcher import ExerciseMatcher
from ..extraction.exercise_normalizer import normalize_exercises
from .dependencies import get_analytics_db, get_user_id

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
    has_note: bool = False
    has_workout: bool = False


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
    calories: Optional[int] = None


class Correlations(BaseModel):
    """Correlation coefficients between metrics."""

    sleep_mood: Optional[float] = None
    sleep_energy: Optional[float] = None
    activity_mood: Optional[float] = None
    activity_energy: Optional[float] = None
    stress_mood: Optional[float] = None
    calories_mood: Optional[float] = None
    calories_energy: Optional[float] = None


class CorrelationResponse(BaseModel):
    """Response for correlation endpoint."""

    entries: list[CorrelationEntry]
    correlations: Correlations


class NutritionDayEntry(BaseModel):
    """Single day of nutrition data."""

    date: str
    total_calories: int = 0
    total_protein_g: int = 0
    total_carbs_g: int = 0
    total_fat_g: int = 0
    meal_count: int = 0


class NutritionSummary(BaseModel):
    """Aggregated nutrition summary."""

    avg_calories: int = 0
    avg_protein_g: int = 0
    avg_carbs_g: int = 0
    avg_fat_g: int = 0
    total_days_tracked: int = 0
    total_meals: int = 0


class NutritionResponse(BaseModel):
    """Response for nutrition/eating habits endpoint."""

    days: list[NutritionDayEntry]
    summary: NutritionSummary
    period: Period


class MuscleGroupEntry(BaseModel):
    """Training data for a single muscle group."""

    muscle_group: str
    sessions: int
    total_sets: int
    exercises: list[str]


class MuscleGroupsResponse(BaseModel):
    """Response for muscle groups trained endpoint."""

    muscle_groups: list[MuscleGroupEntry]
    period: Period


# ── Dependency helpers (must be above all endpoint definitions) ──────────────


def get_db(request: Request, _user_id: str = Depends(get_user_id)):
    """Get analytics database for dashboard reads.

    Depends on get_user_id to ensure the analytics cache is populated
    on the first authenticated request (cloud mode).
    """
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


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/nutrition", response_model=NutritionResponse)
def get_nutrition_data(
    days: int = Query(default=30, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> NutritionResponse:
    """Get nutrition and eating habits data over a time period.

    Returns daily calorie and macronutrient totals and averages.
    """
    period = get_period(days)

    result = db.execute(
        """
        SELECT
            date,
            COALESCE(SUM(calories), 0) as total_calories,
            COALESCE(SUM(protein_g), 0) as total_protein,
            COALESCE(SUM(carbs_g), 0) as total_carbs,
            COALESCE(SUM(fat_g), 0) as total_fat,
            COUNT(*) as meal_count
        FROM food_log
        WHERE date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date ASC
        """,
        [period.start_date, period.end_date],
    ).fetchall()

    day_entries = [
        NutritionDayEntry(
            date=str(row[0]),
            total_calories=int(row[1]),
            total_protein_g=int(row[2]),
            total_carbs_g=int(row[3]),
            total_fat_g=int(row[4]),
            meal_count=int(row[5]),
        )
        for row in result
    ]

    total_days = len(day_entries)
    total_meals = sum(d.meal_count for d in day_entries)
    # Only average over days that have actual calorie data (non-zero)
    days_with_calories = [d for d in day_entries if d.total_calories > 0]
    cal_days = len(days_with_calories)
    summary = NutritionSummary(
        avg_calories=round(sum(d.total_calories for d in days_with_calories) / cal_days) if cal_days else 0,
        avg_protein_g=round(sum(d.total_protein_g for d in days_with_calories) / cal_days) if cal_days else 0,
        avg_carbs_g=round(sum(d.total_carbs_g for d in days_with_calories) / cal_days) if cal_days else 0,
        avg_fat_g=round(sum(d.total_fat_g for d in days_with_calories) / cal_days) if cal_days else 0,
        total_days_tracked=total_days,
        total_meals=total_meals,
    )

    return NutritionResponse(
        days=day_entries,
        summary=summary,
        period=period,
    )


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

    # Combined summary + current max in a single query (avoids N+1)
    summary_row = db.execute(
        """
        WITH summary AS (
            SELECT
                MAX(weight_kg) as all_time_max,
                SUM(COALESCE(weight_kg, 0) * COALESCE(reps, 0)) as total_volume,
                COUNT(DISTINCT date) as total_sessions
            FROM exercise_log
            WHERE exercise_name = ?
        ),
        current AS (
            SELECT MAX(weight_kg) as current_max
            FROM exercise_log
            WHERE exercise_name = ? AND date = (
                SELECT MAX(date) FROM exercise_log WHERE exercise_name = ?
            )
        )
        SELECT s.all_time_max, s.total_volume, s.total_sessions, c.current_max
        FROM summary s, current c
        """,
        [exercise, exercise, exercise],
    ).fetchone()

    summary = ExerciseSummary(
        current_max=float(summary_row[3]) if summary_row and summary_row[3] else None,
        all_time_max=float(summary_row[0]) if summary_row and summary_row[0] else None,
        total_volume=int(summary_row[1]) if summary_row and summary_row[1] else 0,
        total_sessions=summary_row[2] if summary_row else 0,
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

    # Get last daily note date — check both extraction_log paths and daily_metrics dates
    import re as _re
    last_daily_note = None

    # Method 1: most recent date in daily_metrics (most reliable)
    metrics_date_row = db.execute(
        "SELECT MAX(date) FROM daily_metrics"
    ).fetchone()
    if metrics_date_row and metrics_date_row[0]:
        last_daily_note = str(metrics_date_row[0])

    # Method 2: extraction_log file paths (fallback if no metrics)
    if not last_daily_note:
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

    # Get activity data
    activity_result = db.execute(
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
    activity_map: dict[str, tuple[int, int]] = {
        str(row[0]): (row[1], int(row[2])) for row in activity_result
    }

    # Get daily note dates (from daily_metrics)
    note_dates_result = db.execute(
        """
        SELECT DISTINCT date FROM daily_metrics
        WHERE date >= ? AND date <= ?
        """,
        [start_date, end_date],
    ).fetchall()
    note_dates = {str(row[0]) for row in note_dates_result}

    # Merge: all dates that have either activity or note
    all_dates = set(activity_map.keys()) | note_dates
    days = []
    for d in sorted(all_dates):
        count, duration = activity_map.get(d, (0, 0))
        days.append(HeatmapDay(
            date=d,
            count=count,
            duration_minutes=duration,
            has_note=d in note_dates,
            has_workout=d in activity_map,
        ))

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

    # Get metrics with activity and food data joined
    result = db.execute(
        """
        SELECT
            m.date,
            m.sleep_hours,
            m.energy,
            m.mood,
            m.stress,
            COALESCE(a.total_minutes, 0) as activity_minutes,
            f.total_calories
        FROM daily_metrics m
        LEFT JOIN (
            SELECT date, SUM(duration_minutes) as total_minutes
            FROM activities
            GROUP BY date
        ) a ON m.date = a.date
        LEFT JOIN (
            SELECT date, SUM(calories) as total_calories
            FROM food_log
            GROUP BY date
        ) f ON m.date = f.date
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
            calories=int(row[6]) if row[6] is not None else None,
        )
        for row in result
    ]

    # Calculate correlations per-pair (only require the two relevant metrics)
    def pair_values(
        field_a: str, field_b: str,
    ) -> tuple[list[float], list[float]]:
        xs, ys = [], []
        for e in entries:
            a = getattr(e, field_a)
            b = getattr(e, field_b)
            if a is not None and b is not None:
                xs.append(float(a))
                ys.append(float(b))
        return xs, ys

    sleep_m, mood_m = pair_values("sleep_hours", "mood")
    sleep_e, energy_e = pair_values("sleep_hours", "energy")
    act_m, mood_a = pair_values("activity_minutes", "mood")
    act_e, energy_a = pair_values("activity_minutes", "energy")
    stress_v, mood_s = pair_values("stress", "mood")
    cal_m, mood_c = pair_values("calories", "mood")
    cal_e, energy_c = pair_values("calories", "energy")

    correlations = Correlations(
        sleep_mood=calculate_correlation(sleep_m, mood_m),
        sleep_energy=calculate_correlation(sleep_e, energy_e),
        activity_mood=calculate_correlation(act_m, mood_a),
        activity_energy=calculate_correlation(act_e, energy_a),
        stress_mood=calculate_correlation(stress_v, mood_s),
        calories_mood=calculate_correlation(cal_m, mood_c),
        calories_energy=calculate_correlation(cal_e, energy_c),
    )

    return CorrelationResponse(
        entries=entries,
        correlations=correlations,
    )


class ActivityGroupEntry(BaseModel):
    """A high-level activity group with entry count."""

    group_name: str
    entry_count: int
    subtypes: list[str] = []


class ActivityGroupResponse(BaseModel):
    """Response for activity groups endpoint."""

    groups: list[ActivityGroupEntry]
    total_entries: int
    period: Period


# Mapping from raw activity_type to high-level group
_ACTIVITY_GROUP_MAP: dict[str, str] = {
    "strength": "Strength Training",
    "bjj": "BJJ / Martial Arts",
    "cardio": "Running / Cardio",
    "running": "Running / Cardio",
    "cycling": "Cycling",
    "swimming": "Swimming",
    "yoga": "Yoga / Mobility",
    "stretching": "Yoga / Mobility",
    "recovery": "Recovery",
    "walk": "Walking",
    "hiit": "HIIT",
    "other": "Other",
}


def _group_activity(activity_type: str) -> str:
    """Map an activity_type to its high-level group name."""
    return _ACTIVITY_GROUP_MAP.get(activity_type.lower(), activity_type.title())


@router.get("/activity-groups", response_model=ActivityGroupResponse)
def get_activity_groups(
    days: int = Query(default=30, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> ActivityGroupResponse:
    """Get activities grouped at a high level with entry counts (not duration).

    Groups similar activity types together (e.g. cardio + running = Running / Cardio).
    Uses entry counts instead of time estimates for accuracy.
    """
    period = get_period(days)

    result = db.execute(
        """
        SELECT activity_type, COUNT(*) as count
        FROM activities
        WHERE date >= ? AND date <= ?
        GROUP BY activity_type
        ORDER BY count DESC
        """,
        [period.start_date, period.end_date],
    ).fetchall()

    groups: dict[str, dict] = {}
    for row in result:
        raw_type = row[0]
        count = row[1]
        group_name = _group_activity(raw_type)

        if group_name in groups:
            groups[group_name]["entry_count"] += count
            if raw_type not in groups[group_name]["subtypes"]:
                groups[group_name]["subtypes"].append(raw_type)
        else:
            groups[group_name] = {
                "group_name": group_name,
                "entry_count": count,
                "subtypes": [raw_type],
            }

    sorted_groups = sorted(groups.values(), key=lambda g: g["entry_count"], reverse=True)
    total = sum(g["entry_count"] for g in sorted_groups)

    return ActivityGroupResponse(
        groups=[ActivityGroupEntry(**g) for g in sorted_groups],
        total_entries=total,
        period=period,
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
                MAX(weight_kg) as last_weight_kg,
                ROW_NUMBER() OVER (
                    PARTITION BY exercise_name
                    ORDER BY date DESC
                ) as rn
            FROM filtered
            GROUP BY exercise_name, date
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


def _load_json_config(filename: str, request: Request = None, user_id: str = None) -> dict:
    """Load a JSON config file. Checks user_settings (Postgres) first, then data dir."""
    import json

    # In hybrid/postgres mode, check user_settings table
    if request and user_id:
        from ..db.sql_compat import get_dialect
        from ..db.user_settings import UserSettingsStore
        db = request.app.state.db
        if get_dialect(db) == "postgres":
            key = filename.removesuffix(".json")
            store = UserSettingsStore(db, user_id)
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
    user_id: str = Depends(get_user_id),
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
    training_config = _load_json_config("training_config.json", request, user_id)
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


# ── Endurance Sports Tracking ───────────────────────────────────────────────

class BodyWeightEntry(BaseModel):
    """Single body weight measurement."""

    date: str
    weight_kg: float


class BodyWeightResponse(BaseModel):
    """Response for body weight endpoint."""

    entries: list[BodyWeightEntry]
    current_kg: Optional[float] = None
    period_change_kg: Optional[float] = None
    period: Period


@router.get("/body-weight", response_model=BodyWeightResponse)
def get_body_weight(
    days: int = Query(default=90, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> BodyWeightResponse:
    """Get body weight trend over time.

    Returns weight entries where weight_kg is recorded, plus
    the most recent weight and change over the period.
    """
    period = get_period(days)

    result = db.execute(
        """
        SELECT date, weight_kg
        FROM daily_metrics
        WHERE weight_kg IS NOT NULL AND date >= ? AND date <= ?
        ORDER BY date ASC
        """,
        [period.start_date, period.end_date],
    ).fetchall()

    entries = [
        BodyWeightEntry(date=str(row[0]), weight_kg=float(row[1]))
        for row in result
    ]

    current_kg = entries[-1].weight_kg if entries else None
    period_change_kg = None
    if len(entries) >= 2:
        period_change_kg = round(entries[-1].weight_kg - entries[0].weight_kg, 1)

    return BodyWeightResponse(
        entries=entries,
        current_kg=current_kg,
        period_change_kg=period_change_kg,
        period=period,
    )


ENDURANCE_SPORTS = ("running", "cycling", "swimming")


class EnduranceCreate(BaseModel):
    date: date
    sport: Literal["running", "cycling", "swimming"]
    distance_km: Optional[float] = Field(None, ge=0)
    duration_minutes: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class EnduranceCreateResponse(BaseModel):
    activity_id: str
    exercise_id: str
    message: str


class EnduranceEntry(BaseModel):
    date: str
    sport: str
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    pace_min_per_km: Optional[float] = None
    speed_kmh: Optional[float] = None
    notes: Optional[str] = None


class EnduranceTableResponse(BaseModel):
    entries: list[EnduranceEntry]
    total_count: int
    offset: int
    limit: int


class EnduranceProgressEntry(BaseModel):
    date: str
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    pace_min_per_km: Optional[float] = None
    speed_kmh: Optional[float] = None


class EnduranceProgressSummary(BaseModel):
    total_distance_km: float
    total_duration_minutes: int
    total_sessions: int
    avg_pace_min_per_km: Optional[float] = None
    best_pace_min_per_km: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    best_speed_kmh: Optional[float] = None
    longest_distance_km: Optional[float] = None


class EnduranceProgressResponse(BaseModel):
    sport: str
    progress: list[EnduranceProgressEntry]
    summary: EnduranceProgressSummary
    period: Period


def _calc_pace(distance_km: Optional[float], duration_minutes: Optional[int]) -> Optional[float]:
    """Calculate pace in min/km. Returns None if inputs are missing or zero."""
    if distance_km and duration_minutes and distance_km > 0:
        return round(duration_minutes / distance_km, 2)
    return None


def _calc_speed(distance_km: Optional[float], duration_minutes: Optional[int]) -> Optional[float]:
    """Calculate speed in km/h. Returns None if inputs are missing or zero."""
    if distance_km and duration_minutes and duration_minutes > 0:
        return round(distance_km / (duration_minutes / 60), 2)
    return None


@router.post("/endurance", status_code=201, response_model=EnduranceCreateResponse)
def create_endurance_activity(
    entry: EnduranceCreate,
    db: DatabaseManager = Depends(get_db),
) -> EnduranceCreateResponse:
    """Log an endurance activity (running, cycling, swimming).

    Creates both an activities record and an exercise_log record.
    """
    activity_id = f"{entry.date.strftime('%Y%m%d')}_{entry.sport[:3]}_manual"
    exercise_id = str(uuid.uuid4())

    # Insert activity
    db.execute(
        """
        INSERT INTO activities (id, date, activity_type, duration_minutes, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        [activity_id, str(entry.date), entry.sport, entry.duration_minutes, entry.notes],
    )

    # Insert exercise_log entry with distance/duration
    db.execute(
        """
        INSERT INTO exercise_log (
            id, activity_id, date, exercise_name,
            distance_km, duration_minutes, notes,
            source_file, extracted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'manual_entry', CURRENT_TIMESTAMP)
        """,
        [
            exercise_id,
            activity_id,
            str(entry.date),
            entry.sport.title(),
            entry.distance_km,
            entry.duration_minutes,
            entry.notes,
        ],
    )

    return EnduranceCreateResponse(
        activity_id=activity_id,
        exercise_id=exercise_id,
        message=f"{entry.sport.title()} activity logged successfully",
    )


@router.get("/endurance-table", response_model=EnduranceTableResponse)
def get_endurance_table(
    sport: Optional[str] = Query(default=None, description="Filter by sport"),
    days: int = Query(default=90, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: Literal["date", "distance_km", "duration_minutes", "pace_min_per_km"] = Query(default="date"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    db: DatabaseManager = Depends(get_db),
) -> EnduranceTableResponse:
    """Get a summary table of endurance sessions."""
    period = get_period(days)

    sport_filter = ""
    params: list[Any] = [period.start_date, period.end_date]
    if sport and sport in ENDURANCE_SPORTS:
        sport_filter = "AND a.activity_type = ?"
        params.append(sport)

    result = db.execute(
        f"""
        SELECT
            a.date,
            a.activity_type,
            el.distance_km,
            el.duration_minutes,
            a.notes
        FROM activities a
        LEFT JOIN exercise_log el ON a.id = el.activity_id
        WHERE a.activity_type IN ('running', 'cycling', 'swimming')
          AND a.date >= ? AND a.date <= ?
          {sport_filter}
        ORDER BY a.date DESC
        """,
        params,
    ).fetchall()

    entries = []
    for row in result:
        dist = float(row[2]) if row[2] is not None else None
        dur = int(row[3]) if row[3] is not None else None
        entries.append(EnduranceEntry(
            date=str(row[0]),
            sport=row[1],
            distance_km=dist,
            duration_minutes=dur,
            pace_min_per_km=_calc_pace(dist, dur),
            speed_kmh=_calc_speed(dist, dur),
            notes=row[4],
        ))

    # Sort
    if sort_by == "pace_min_per_km":
        entries.sort(
            key=lambda e: e.pace_min_per_km if e.pace_min_per_km is not None else float('inf'),
            reverse=(sort_order == "desc"),
        )
    elif sort_by == "distance_km":
        entries.sort(
            key=lambda e: e.distance_km if e.distance_km is not None else -1,
            reverse=(sort_order == "desc"),
        )
    elif sort_by == "duration_minutes":
        entries.sort(
            key=lambda e: e.duration_minutes if e.duration_minutes is not None else -1,
            reverse=(sort_order == "desc"),
        )
    # date sort already handled by SQL ORDER BY

    total_count = len(entries)
    paginated = entries[offset:offset + limit]

    return EnduranceTableResponse(
        entries=paginated,
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


@router.get("/endurance-progress", response_model=EnduranceProgressResponse)
def get_endurance_progress(
    sport: str = Query(..., description="Sport to track (running, cycling, swimming)"),
    days: int = Query(default=90, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
) -> EnduranceProgressResponse:
    """Get time-series progress data for a specific endurance sport."""
    if sport not in ENDURANCE_SPORTS:
        raise HTTPException(status_code=400, detail=f"Invalid sport. Must be one of: {', '.join(ENDURANCE_SPORTS)}")

    period = get_period(days)

    result = db.execute(
        """
        SELECT
            a.date,
            el.distance_km,
            el.duration_minutes
        FROM activities a
        LEFT JOIN exercise_log el ON a.id = el.activity_id
        WHERE a.activity_type = ?
          AND a.date >= ? AND a.date <= ?
        ORDER BY a.date ASC
        """,
        [sport, period.start_date, period.end_date],
    ).fetchall()

    progress = []
    total_dist = 0.0
    total_dur = 0
    paces: list[float] = []
    speeds: list[float] = []
    distances: list[float] = []

    for row in result:
        dist = float(row[1]) if row[1] is not None else None
        dur = int(row[2]) if row[2] is not None else None
        pace = _calc_pace(dist, dur)
        speed = _calc_speed(dist, dur)

        progress.append(EnduranceProgressEntry(
            date=str(row[0]),
            distance_km=dist,
            duration_minutes=dur,
            pace_min_per_km=pace,
            speed_kmh=speed,
        ))

        if dist:
            total_dist += dist
            distances.append(dist)
        if dur:
            total_dur += dur
        if pace:
            paces.append(pace)
        if speed:
            speeds.append(speed)

    summary = EnduranceProgressSummary(
        total_distance_km=round(total_dist, 2),
        total_duration_minutes=total_dur,
        total_sessions=len(progress),
        avg_pace_min_per_km=round(sum(paces) / len(paces), 2) if paces else None,
        best_pace_min_per_km=round(min(paces), 2) if paces else None,
        avg_speed_kmh=round(sum(speeds) / len(speeds), 2) if speeds else None,
        best_speed_kmh=round(max(speeds), 2) if speeds else None,
        longest_distance_km=round(max(distances), 2) if distances else None,
    )

    return EnduranceProgressResponse(
        sport=sport,
        progress=progress,
        summary=summary,
        period=period,
    )


@router.get("/muscle-groups", response_model=MuscleGroupsResponse)
def get_muscle_groups(
    days: int = Query(default=7, ge=1, le=365),
    db: DatabaseManager = Depends(get_db),
    matcher: ExerciseMatcher = Depends(get_exercise_matcher),
) -> MuscleGroupsResponse:
    """Get muscle groups trained in the last N days.

    Maps exercises from exercise_log to muscle groups via exercise_definitions.json.
    """
    import json

    period = get_period(days)

    # Load exercise definitions for muscle group mapping
    exercise_defs = _load_json_config("exercise_definitions.json")

    # Query distinct exercises with session/set counts
    result = db.execute(
        """
        SELECT
            exercise_name,
            COUNT(DISTINCT date) as sessions,
            COUNT(*) as total_sets
        FROM exercise_log
        WHERE date >= ? AND date <= ?
            AND exercise_name IS NOT NULL
        GROUP BY exercise_name
        """,
        [period.start_date, period.end_date],
    ).fetchall()

    # Build muscle group aggregation
    muscle_data: dict[str, dict] = {}
    for row in result:
        raw_name = row[0]
        sessions = row[1]
        total_sets = row[2]

        # Normalize exercise name to canonical form
        canonical, _ = matcher.match(raw_name)
        canonical_key = canonical.lower().replace(" ", "_").replace("-", "_")

        # Look up muscle groups from definitions
        groups = []
        if canonical_key in exercise_defs:
            groups = exercise_defs[canonical_key].get("muscle_groups", [])
        else:
            # Try fuzzy lookup by display name
            for key, defn in exercise_defs.items():
                if defn.get("display", "").lower() == canonical.lower():
                    groups = defn.get("muscle_groups", [])
                    break

        for group in groups:
            if group not in muscle_data:
                muscle_data[group] = {"sessions": 0, "total_sets": 0, "exercises": set()}
            muscle_data[group]["sessions"] = max(muscle_data[group]["sessions"], sessions)
            muscle_data[group]["total_sets"] += total_sets
            muscle_data[group]["exercises"].add(canonical)

    entries = [
        MuscleGroupEntry(
            muscle_group=group,
            sessions=data["sessions"],
            total_sets=data["total_sets"],
            exercises=sorted(data["exercises"]),
        )
        for group, data in sorted(muscle_data.items(), key=lambda x: x[1]["total_sets"], reverse=True)
    ]

    return MuscleGroupsResponse(muscle_groups=entries, period=period)
