"""Insights API endpoints - AI-powered suggestions based on user data."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..logging_config import get_logger
from .dependencies import get_analytics_db

logger = get_logger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


class Insight(BaseModel):
    """Single insight/suggestion."""

    id: str
    type: str  # pattern, trend, reminder, follow_up
    title: str
    message: str
    priority: int  # 1=high, 2=medium, 3=low
    data_source: Optional[str] = None


class DailyInsightsResponse(BaseModel):
    """Response for daily insights endpoint."""

    insights: list[Insight]
    generated_at: str


class WeeklySummaryResponse(BaseModel):
    """Response for weekly summary endpoint."""

    summary: str
    highlights: list[str]
    period_start: str
    period_end: str


def get_db(request: Request):
    """Get analytics database for insights."""
    return get_analytics_db(request)


def get_claude(request: Request) -> ClaudeClient:
    """Get Claude client from app state."""
    return request.app.state.claude


async def _gather_context_data(db: DatabaseManager, days: int = 7) -> dict:
    """Gather recent data for insight generation.

    Consolidates 7 sequential queries into 3 using CTEs.

    Args:
        db: Database manager
        days: Number of days to look back

    Returns:
        Dictionary with context data
    """
    today = date.today()
    start_date = today - timedelta(days=days)

    context = {
        "today": str(today),
        "start_date": str(start_date),
    }

    # Query 1: Activities + food count + activity patterns (consolidated)
    activities = db.execute(
        "SELECT date, activity_type, duration_minutes FROM activities WHERE date >= ? ORDER BY date DESC",
        [str(start_date)],
    ).fetchall()
    context["activities"] = [
        {"date": str(row[0]), "type": row[1], "duration": row[2]}
        for row in activities
    ]

    food_today = db.execute(
        "SELECT COUNT(*) FROM food_log WHERE date = ?", [str(today)]
    ).fetchone()[0]
    context["food_logged_today"] = food_today > 0

    activity_patterns = db.execute(
        """
        SELECT DAYOFWEEK(date) as dow, activity_type, COUNT(*) as count
        FROM activities WHERE date >= ?
        GROUP BY DAYOFWEEK(date), activity_type ORDER BY count DESC
        """,
        [str(today - timedelta(days=30))],
    ).fetchall()
    context["activity_patterns"] = [
        {"day_of_week": row[0], "type": row[1], "count": row[2]}
        for row in activity_patterns
    ]

    # Query 2: Tasks
    incomplete_tasks = db.execute(
        "SELECT date, description, category FROM tasks WHERE status NOT IN ('done', 'cancelled') ORDER BY date DESC LIMIT 10",
    ).fetchall()
    context["incomplete_tasks"] = [
        {"date": str(row[0]), "description": row[1], "category": row[2]}
        for row in incomplete_tasks
    ]

    # Query 3: All metrics + week comparisons in a single CTE query
    metrics_result = db.execute(
        """
        WITH recent AS (
            SELECT date, sleep_hours, sleep_quality, energy, mood, stress
            FROM daily_metrics WHERE date >= ?
        ),
        last_week AS (
            SELECT AVG(sleep_hours) as s, AVG(energy) as e, AVG(mood) as m
            FROM daily_metrics WHERE date >= ? AND date <= ?
        ),
        prev_week AS (
            SELECT AVG(sleep_hours) as s, AVG(energy) as e, AVG(mood) as m
            FROM daily_metrics WHERE date >= ? AND date < ?
        )
        SELECT 'r' as t, date, sleep_hours, sleep_quality, energy, mood, stress FROM recent
        UNION ALL
        SELECT 'l', NULL, s, NULL, e, m, NULL FROM last_week
        UNION ALL
        SELECT 'p', NULL, s, NULL, e, m, NULL FROM prev_week
        """,
        [
            str(start_date),
            str(today - timedelta(days=7)), str(today),
            str(today - timedelta(days=14)), str(today - timedelta(days=7)),
        ],
    ).fetchall()

    metrics = []
    last_week = {"avg_sleep": None, "avg_energy": None, "avg_mood": None}
    prev_week = {"avg_sleep": None, "avg_energy": None, "avg_mood": None}

    for row in metrics_result:
        if row[0] == "r":
            metrics.append({
                "date": str(row[1]),
                "sleep_hours": float(row[2]) if row[2] else None,
                "sleep_quality": row[3],
                "energy": row[4],
                "mood": row[5],
                "stress": row[6],
            })
        elif row[0] == "l":
            last_week = {
                "avg_sleep": float(row[2]) if row[2] else None,
                "avg_energy": float(row[4]) if row[4] else None,
                "avg_mood": float(row[5]) if row[5] else None,
            }
        elif row[0] == "p":
            prev_week = {
                "avg_sleep": float(row[2]) if row[2] else None,
                "avg_energy": float(row[4]) if row[4] else None,
                "avg_mood": float(row[5]) if row[5] else None,
            }

    context["metrics"] = metrics
    context["metrics_comparison"] = {"last_week": last_week, "prev_week": prev_week}

    return context


def _generate_fallback_insights(context: dict) -> list[Insight]:
    """Generate simple insights without Claude when API is unavailable.

    Args:
        context: Data context

    Returns:
        List of basic insights
    """
    insights = []
    insight_id = 0

    # Check for incomplete tasks
    if context.get("incomplete_tasks"):
        task_count = len(context["incomplete_tasks"])
        insights.append(
            Insight(
                id=f"insight_{insight_id}",
                type="follow_up",
                title="Incomplete Tasks",
                message=f"You have {task_count} incomplete task{'s' if task_count > 1 else ''} to follow up on.",
                priority=2,
                data_source="tasks",
            )
        )
        insight_id += 1

    # Check for food logging
    if not context.get("food_logged_today", True):
        insights.append(
            Insight(
                id=f"insight_{insight_id}",
                type="reminder",
                title="Food Log",
                message="You haven't logged any food today. Don't forget to track your meals!",
                priority=3,
                data_source="food_log",
            )
        )
        insight_id += 1

    # Check activity streak
    today = date.today()
    today_str = str(today)
    yesterday_str = str(today - timedelta(days=1))

    activities_today = any(
        a["date"] == today_str for a in context.get("activities", [])
    )
    activities_yesterday = any(
        a["date"] == yesterday_str for a in context.get("activities", [])
    )

    if not activities_today and activities_yesterday:
        insights.append(
            Insight(
                id=f"insight_{insight_id}",
                type="reminder",
                title="Keep Your Streak",
                message="You were active yesterday but haven't logged anything today. Keep the momentum going!",
                priority=2,
                data_source="activities",
            )
        )
        insight_id += 1

    # Add metrics trend if available
    metrics_cmp = context.get("metrics_comparison", {})
    last_week = metrics_cmp.get("last_week", {})
    prev_week = metrics_cmp.get("prev_week", {})

    if last_week.get("avg_sleep") and prev_week.get("avg_sleep"):
        sleep_change = last_week["avg_sleep"] - prev_week["avg_sleep"]
        if abs(sleep_change) >= 0.5:
            direction = "improved" if sleep_change > 0 else "decreased"
            pct = abs(sleep_change / prev_week["avg_sleep"] * 100)
            insights.append(
                Insight(
                    id=f"insight_{insight_id}",
                    type="trend",
                    title="Sleep Trend",
                    message=f"Your sleep has {direction} by {pct:.0f}% compared to last week.",
                    priority=2 if direction == "decreased" else 3,
                    data_source="daily_metrics",
                )
            )
            insight_id += 1

    return insights[:3]  # Return max 3 insights


INSIGHTS_SYSTEM_PROMPT = """You are a helpful wellness assistant analyzing a user's personal data.
Generate 2-3 actionable insights based on the provided data. Focus on:
1. Patterns (e.g., "You usually do X on Mondays")
2. Trends (e.g., "Your sleep improved 12% this month")
3. Reminders (e.g., "You haven't logged food today")
4. Follow-ups (e.g., "3 incomplete tasks from yesterday")

Keep insights brief, positive, and actionable. Use specific numbers when available.
IMPORTANT: Only generate insights based on data that is actually present. If a data category is empty (empty array []), do NOT fabricate or assume data for it. Only reference data you can see.
Return ONLY a JSON array of insights, no explanation.

Each insight should have:
- type: "pattern", "trend", "reminder", or "follow_up"
- title: Short title (3-5 words)
- message: One sentence insight
- priority: 1 (high), 2 (medium), or 3 (low)"""


@router.get("/daily", response_model=DailyInsightsResponse)
async def get_daily_insights(
    db: DatabaseManager = Depends(get_db),
    claude: ClaudeClient = Depends(get_claude),
) -> DailyInsightsResponse:
    """Get AI-generated daily insights based on recent data.

    Returns:
        Daily insights with actionable suggestions
    """
    import json

    context = await _gather_context_data(db, days=7)

    # If Claude is not configured, return fallback insights
    if not claude.is_configured:
        return DailyInsightsResponse(
            insights=_generate_fallback_insights(context),
            generated_at=context["today"],
        )

    # Guard: skip AI call if there's no meaningful data to analyze
    has_data = (
        context.get("activities")
        or context.get("metrics")
        or context.get("incomplete_tasks")
        or context.get("activity_patterns")
    )
    if not has_data:
        return DailyInsightsResponse(
            insights=[
                Insight(
                    id="insight_0",
                    type="reminder",
                    title="No Data Yet",
                    message="Start logging activities, meals, or daily metrics to get personalized insights.",
                    priority=3,
                )
            ],
            generated_at=context["today"],
        )

    # Generate insights with Claude
    try:
        prompt = f"""Analyze this user data and generate 2-3 insights:

Today: {context['today']}

Recent Activities (last 7 days):
{json.dumps(context['activities'], indent=2)}

Daily Metrics (last 7 days):
{json.dumps(context['metrics'], indent=2)}

Incomplete Tasks:
{json.dumps(context['incomplete_tasks'], indent=2)}

Food logged today: {context['food_logged_today']}

Activity Patterns (last 30 days by day of week):
{json.dumps(context['activity_patterns'], indent=2)}

Metrics Comparison (this week vs last week):
{json.dumps(context['metrics_comparison'], indent=2)}

Return a JSON array of insights. Example format:
[
  {{"type": "pattern", "title": "Monday Workouts", "message": "You usually log strength training on Mondays.", "priority": 3}},
  {{"type": "reminder", "title": "Food Log", "message": "You haven't logged any food today.", "priority": 2}}
]"""

        response = await claude.query(prompt, INSIGHTS_SYSTEM_PROMPT)

        # Parse the JSON response
        # Handle potential markdown code blocks
        response_text = response.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        insights_data = json.loads(response_text)

        insights = [
            Insight(
                id=f"insight_{i}",
                type=item.get("type", "pattern"),
                title=item.get("title", "Insight"),
                message=item.get("message", ""),
                priority=item.get("priority", 2),
                data_source=item.get("data_source"),
            )
            for i, item in enumerate(insights_data[:3])
        ]

        return DailyInsightsResponse(
            insights=insights,
            generated_at=context["today"],
        )

    except Exception:
        logger.warning("insights_generation_failed", exc_info=True)
        # Fallback to basic insights on error
        return DailyInsightsResponse(
            insights=_generate_fallback_insights(context),
            generated_at=context["today"],
        )


@router.get("/weekly", response_model=WeeklySummaryResponse)
async def get_weekly_summary(
    db: DatabaseManager = Depends(get_db),
    claude: ClaudeClient = Depends(get_claude),
) -> WeeklySummaryResponse:
    """Get AI-generated weekly summary with trends and insights.

    Returns:
        Weekly summary with highlights
    """
    import json

    context = await _gather_context_data(db, days=7)

    today = date.today()
    period_start = str(today - timedelta(days=6))
    period_end = str(today)

    # If Claude is not configured, return basic summary
    if not claude.is_configured:
        activity_count = len(context.get("activities", []))
        metrics_count = len(context.get("metrics", []))

        highlights = []
        if activity_count > 0:
            highlights.append(f"Logged {activity_count} activities this week")
        if metrics_count > 0:
            highlights.append(f"Tracked daily metrics for {metrics_count} days")

        incomplete = len(context.get("incomplete_tasks", []))
        if incomplete > 0:
            highlights.append(f"{incomplete} tasks still pending")

        return WeeklySummaryResponse(
            summary="Here's your week at a glance. Configure Claude API for personalized insights.",
            highlights=highlights if highlights else ["No data logged this week"],
            period_start=period_start,
            period_end=period_end,
        )

    # Generate summary with Claude
    try:
        prompt = f"""Create a brief weekly summary for this user.

Period: {period_start} to {period_end}

Activities:
{json.dumps(context['activities'], indent=2)}

Daily Metrics:
{json.dumps(context['metrics'], indent=2)}

Incomplete Tasks:
{json.dumps(context['incomplete_tasks'], indent=2)}

Metrics Comparison:
{json.dumps(context['metrics_comparison'], indent=2)}

Return a JSON object with:
- summary: A 1-2 sentence personalized summary
- highlights: Array of 2-4 bullet points (strings) with key achievements or areas for attention

Example:
{{
  "summary": "Great week with consistent exercise! Your sleep quality improved notably.",
  "highlights": ["5 workout sessions completed", "Sleep up 15% from last week", "2 tasks pending review"]
}}"""

        response = await claude.query(prompt, INSIGHTS_SYSTEM_PROMPT)

        # Parse the JSON response
        response_text = response.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        summary_data = json.loads(response_text)

        return WeeklySummaryResponse(
            summary=summary_data.get("summary", "Week in review"),
            highlights=summary_data.get("highlights", [])[:4],
            period_start=period_start,
            period_end=period_end,
        )

    except Exception:
        logger.warning("weekly_summary_generation_failed", exc_info=True)
        # Fallback to basic summary
        return WeeklySummaryResponse(
            summary="Here's your week at a glance.",
            highlights=["Unable to generate detailed summary"],
            period_start=period_start,
            period_end=period_end,
        )


@router.post("/dismiss/{insight_id}")
async def dismiss_insight(insight_id: str) -> dict:
    """Dismiss an insight (client-side tracking only for now).

    Args:
        insight_id: ID of insight to dismiss

    Returns:
        Confirmation message
    """
    # In a full implementation, we'd store dismissed insights in the DB
    # For now, just acknowledge the request (frontend handles local storage)
    return {"status": "dismissed", "insight_id": insight_id}
