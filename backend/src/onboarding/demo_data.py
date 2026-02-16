"""Pure functions for generating realistic demo data.

All functions are deterministic (seeded RNG) and return plain dicts
ready for DB insertion. No DB or IO dependencies.
"""

import random
from datetime import date, timedelta
from typing import Any

from .constants import DEMO_DAYS, DEMO_SOURCE_FILE

# Fixed seed for reproducibility
_SEED = 42

# ── Exercise definitions (subset of shared/exercise_definitions.json) ──────

_STRENGTH_EXERCISES: dict[str, list[dict[str, Any]]] = {
    "upper": [
        {"name": "bench_press", "base_weight": 80, "reps": 8},
        {"name": "military_press", "base_weight": 50, "reps": 8},
        {"name": "barbell_row", "base_weight": 70, "reps": 8},
        {"name": "lat_pulldown", "base_weight": 60, "reps": 10},
    ],
    "lower": [
        {"name": "squat", "base_weight": 100, "reps": 6},
        {"name": "deadlift", "base_weight": 120, "reps": 5},
        {"name": "leg_press", "base_weight": 180, "reps": 10},
        {"name": "leg_curl", "base_weight": 40, "reps": 12},
    ],
}

_MEAL_TEMPLATES = [
    {"meal_type": "breakfast", "time": "07:30", "desc": "Oats with berries and protein shake", "cal": 520, "p": 35, "c": 65, "f": 12},
    {"meal_type": "breakfast", "time": "08:00", "desc": "Eggs, toast, and avocado", "cal": 480, "p": 28, "c": 40, "f": 22},
    {"meal_type": "lunch", "time": "12:00", "desc": "Chicken breast with rice and vegetables", "cal": 650, "p": 45, "c": 70, "f": 15},
    {"meal_type": "lunch", "time": "12:30", "desc": "Salmon salad with quinoa", "cal": 580, "p": 40, "c": 45, "f": 20},
    {"meal_type": "dinner", "time": "18:30", "desc": "Steak with sweet potato and broccoli", "cal": 720, "p": 50, "c": 55, "f": 25},
    {"meal_type": "dinner", "time": "19:00", "desc": "Pasta with meat sauce and side salad", "cal": 680, "p": 35, "c": 80, "f": 18},
    {"meal_type": "snack", "time": "15:00", "desc": "Greek yogurt with nuts", "cal": 280, "p": 20, "c": 15, "f": 14},
]

_TASK_TEMPLATES = [
    {"desc": "Review quarterly goals", "cat": "work", "pri": 2, "status": "done"},
    {"desc": "Update project documentation", "cat": "work", "pri": 3, "status": "done"},
    {"desc": "Schedule dentist appointment", "cat": "personal", "pri": 2, "status": "done"},
    {"desc": "Submit expense report", "cat": "work", "pri": 1, "status": "done"},
    {"desc": "Research meal prep recipes", "cat": "health", "pri": 3, "status": "done"},
    {"desc": "Clean out garage", "cat": "personal", "pri": 4, "status": "done"},
    {"desc": "Prepare presentation slides", "cat": "work", "pri": 1, "status": "done"},
    {"desc": "Order new running shoes", "cat": "health", "pri": 3, "status": "done"},
    {"desc": "Set up automated backups", "cat": "work", "pri": 2, "status": "backlog"},
    {"desc": "Plan weekend hiking trip", "cat": "personal", "pri": 3, "status": "backlog"},
    {"desc": "Read chapter 5 of current book", "cat": "personal", "pri": 4, "status": "backlog"},
    {"desc": "Organize digital photo library", "cat": "personal", "pri": 4, "status": "backlog"},
    {"desc": "Write blog post draft", "cat": "work", "pri": 3, "status": "backlog"},
    {"desc": "Refactor authentication module", "cat": "work", "pri": 1, "status": "in_progress"},
    {"desc": "Train for 10K race", "cat": "health", "pri": 2, "status": "in_progress"},
    {"desc": "Learn TypeScript generics", "cat": "work", "pri": 2, "status": "in_progress"},
    {"desc": "Migrate database to new schema", "cat": "work", "pri": 1, "status": "in_progress"},
    {"desc": "Fix CI pipeline flaky tests", "cat": "work", "pri": 2, "status": "cancelled"},
    {"desc": "Build custom Slack integration", "cat": "work", "pri": 3, "status": "cancelled"},
    {"desc": "Start sourdough baking", "cat": "personal", "pri": 4, "status": "cancelled"},
]


def generate_demo_data(today: date | None = None) -> dict[str, list[dict[str, Any]]]:
    """Generate 30 days of realistic demo data.

    Returns a dict with keys: activities, exercise_log, daily_metrics, food_log, tasks.
    Each value is a list of row dicts ready for DB insertion.
    """
    rng = random.Random(_SEED)
    if today is None:
        today = date.today()

    activities: list[dict[str, Any]] = []
    exercise_log: list[dict[str, Any]] = []
    daily_metrics: list[dict[str, Any]] = []
    food_log: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []

    # Track progressive overload per exercise
    weight_progress: dict[str, float] = {}

    for day_offset in range(DEMO_DAYS):
        d = today - timedelta(days=DEMO_DAYS - 1 - day_offset)
        d_str = d.isoformat()
        weekday = d.weekday()  # 0=Mon ... 6=Sun

        # ── Daily Metrics (every day) ──────────────────────────────
        # Slight upward trend in mood/energy over 30 days
        trend = day_offset / DEMO_DAYS  # 0.0 → 1.0
        daily_metrics.append({
            "date": d_str,
            "sleep_hours": round(rng.uniform(6.5, 8.5), 1),
            "sleep_quality": rng.randint(5, 9),
            "energy": min(10, max(1, int(rng.gauss(6 + trend * 1.5, 1.2)))),
            "mood": min(10, max(1, int(rng.gauss(6.5 + trend * 1.5, 1.0)))),
            "stress": min(10, max(1, int(rng.gauss(4 - trend * 1.0, 1.5)))),
            "notes": None,
            "source_file": DEMO_SOURCE_FILE,
        })

        # ── Activities & Exercise Log ──────────────────────────────
        if weekday in (0, 3):  # Mon, Thu → Strength
            group = "upper" if weekday == 0 else "lower"
            activity_id = f"demo_{d_str}_strength_{group}"
            activities.append({
                "id": activity_id,
                "date": d_str,
                "activity_type": "strength",
                "duration_minutes": 60,
                "notes": f"{group.title()} body strength session",
                "source_file": DEMO_SOURCE_FILE,
            })

            for j, ex in enumerate(_STRENGTH_EXERCISES[group]):
                name = ex["name"]
                if name not in weight_progress:
                    weight_progress[name] = float(ex["base_weight"])
                else:
                    weight_progress[name] += rng.uniform(0.5, 2.5)

                for set_num in range(1, 4):  # 3 sets
                    exercise_log.append({
                        "id": f"demo_{d_str}_{name}_{set_num}",
                        "activity_id": activity_id,
                        "date": d_str,
                        "exercise_name": name,
                        "weight_kg": round(weight_progress[name], 1),
                        "reps": ex["reps"] + rng.randint(-1, 1),
                        "set_number": set_num,
                        "duration_minutes": None,
                        "distance_km": None,
                        "notes": None,
                        "source_file": DEMO_SOURCE_FILE,
                    })

        elif weekday in (1, 4):  # Tue, Fri → BJJ
            activity_id = f"demo_{d_str}_bjj"
            activities.append({
                "id": activity_id,
                "date": d_str,
                "activity_type": "bjj",
                "duration_minutes": 90,
                "notes": "BJJ training session",
                "source_file": DEMO_SOURCE_FILE,
            })

        elif weekday == 5 and rng.random() > 0.3:  # ~70% of Saturdays → Cardio
            activity_id = f"demo_{d_str}_cardio"
            activities.append({
                "id": activity_id,
                "date": d_str,
                "activity_type": "cardio",
                "duration_minutes": 45,
                "notes": "Weekend cardio session",
                "source_file": DEMO_SOURCE_FILE,
            })

        # ── Food Log (~15 of 30 days, 2-3 meals each) ─────────────
        if rng.random() > 0.5:
            n_meals = rng.choice([2, 2, 3])
            chosen_meals = rng.sample(_MEAL_TEMPLATES, min(n_meals, len(_MEAL_TEMPLATES)))
            for meal in chosen_meals:
                food_log.append({
                    "id": f"demo_{d_str}_{meal['meal_type']}_{rng.randint(1000, 9999)}",
                    "date": d_str,
                    "meal_type": meal["meal_type"],
                    "time": meal["time"],
                    "description": meal["desc"],
                    "calories": meal["cal"] + rng.randint(-50, 50),
                    "protein_g": meal["p"] + rng.randint(-5, 5),
                    "carbs_g": meal["c"] + rng.randint(-10, 10),
                    "fat_g": meal["f"] + rng.randint(-3, 3),
                    "notes": None,
                    "source_file": DEMO_SOURCE_FILE,
                })

    # ── Tasks (date-independent, spread across last 30 days) ───────
    for i, tmpl in enumerate(_TASK_TEMPLATES):
        # Spread task dates across the 30-day window
        task_date = today - timedelta(days=rng.randint(0, DEMO_DAYS - 1))
        completed_at = None
        if tmpl["status"] in ("done", "cancelled"):
            completed_at = (task_date + timedelta(days=rng.randint(0, 3))).isoformat() + "T12:00:00"

        tasks.append({
            "id": f"demo_task_{i+1:03d}",
            "date": task_date.isoformat(),
            "description": tmpl["desc"],
            "status": tmpl["status"],
            "completed_at": completed_at,
            "category": tmpl["cat"],
            "priority": tmpl["pri"],
            "source_file": DEMO_SOURCE_FILE,
        })

    return {
        "activities": activities,
        "exercise_log": exercise_log,
        "daily_metrics": daily_metrics,
        "food_log": food_log,
        "tasks": tasks,
    }
