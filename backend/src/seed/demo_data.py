"""Generate demo seed data for exercises, food, and daily metrics.

Usage:
    python -m src.seed.demo_data --data-path ./data

Or automatically on startup when DEMO_MODE=true.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Exercise definitions
# ---------------------------------------------------------------------------

EXERCISES = [
    ("Squat", "legs", 100, 140),
    ("Deadlift", "back", 100, 150),
    ("Bench Press", "chest", 60, 100),
    ("Overhead Press", "shoulders", 40, 60),
    ("Barbell Row", "back", 60, 90),
    ("Pull-ups", "back", 0, 0),  # bodyweight
    ("Romanian Deadlift", "legs", 80, 120),
    ("Leg Press", "legs", 120, 200),
    ("Dumbbell Curl", "arms", 10, 18),
    ("Tricep Dips", "arms", 0, 0),  # bodyweight
]

WORKOUT_TYPES = ["Strength", "BJJ", "Cardio", "Cycling", "Rest"]

MEALS = [
    ("Oatmeal with banana", 350, 12, 55, 8),
    ("Protein shake", 320, 40, 20, 8),
    ("Eggs and toast", 420, 28, 30, 22),
    ("Chicken salad", 450, 42, 15, 24),
    ("Salmon bowl", 580, 38, 45, 28),
    ("Pasta with meatballs", 650, 35, 70, 22),
    ("Stir fry with rice", 520, 30, 55, 18),
    ("Greek yogurt with granola", 380, 22, 42, 14),
    ("Turkey sandwich", 420, 32, 38, 16),
    ("Burrito bowl", 600, 36, 52, 24),
]


def generate_exercise_log(start_date: date, days: int = 14) -> list[dict]:
    """Generate realistic exercise log entries."""
    rows = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        workout_type = random.choice(WORKOUT_TYPES)

        if workout_type == "Rest":
            continue
        if workout_type in ("BJJ", "Cardio", "Cycling"):
            rows.append({
                "date": d.isoformat(),
                "exercise_name": workout_type,
                "sets": 1,
                "reps": 1,
                "weight_kg": 0,
                "notes": f"{random.randint(30, 60)} minutes",
            })
            continue

        # Strength day: 3-5 exercises
        day_exercises = random.sample(EXERCISES, k=random.randint(3, 5))
        for name, _, low, high in day_exercises:
            weight = random.randint(low, high) if high > 0 else 0
            sets = random.randint(3, 5)
            reps = random.randint(5, 12)
            rows.append({
                "date": d.isoformat(),
                "exercise_name": name,
                "sets": sets,
                "reps": reps,
                "weight_kg": weight,
                "notes": "",
            })
    return rows


def generate_food_log(start_date: date, days: int = 14) -> list[dict]:
    """Generate realistic food log entries."""
    rows = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        # 2-4 meals per day
        day_meals = random.sample(MEALS, k=random.randint(2, 4))
        for name, cal, protein, carbs, fat in day_meals:
            # Add some variance
            cal_var = cal + random.randint(-50, 50)
            rows.append({
                "date": d.isoformat(),
                "meal_name": name,
                "calories": cal_var,
                "protein_g": protein + random.randint(-3, 3),
                "carbs_g": carbs + random.randint(-5, 5),
                "fat_g": fat + random.randint(-3, 3),
            })
    return rows


def generate_daily_metrics(start_date: date, days: int = 14) -> list[dict]:
    """Generate realistic daily metrics."""
    rows = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        rows.append({
            "date": d.isoformat(),
            "sleep_hours": round(random.uniform(5.5, 9.0), 1),
            "energy": random.randint(4, 10),
            "mood": random.randint(5, 10),
        })
    return rows


def seed_database(db, days: int = 14) -> dict[str, int]:
    """Insert demo data into the database.

    Args:
        db: DatabaseManager instance
        days: Number of days of data to generate

    Returns:
        Dict with counts of inserted rows per table
    """
    start = date.today() - timedelta(days=days)

    exercises = generate_exercise_log(start, days)
    food = generate_food_log(start, days)
    metrics = generate_daily_metrics(start, days)

    counts = {}

    # Insert exercises
    for row in exercises:
        db.execute(
            "INSERT INTO exercise_log (date, exercise_name, sets, reps, weight_kg, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [row["date"], row["exercise_name"], row["sets"], row["reps"], row["weight_kg"], row["notes"]],
        )
    counts["exercise_log"] = len(exercises)

    # Insert food
    for row in food:
        db.execute(
            "INSERT INTO food_log (date, meal_name, calories, protein_g, carbs_g, fat_g) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [row["date"], row["meal_name"], row["calories"], row["protein_g"], row["carbs_g"], row["fat_g"]],
        )
    counts["food_log"] = len(food)

    # Insert metrics
    for row in metrics:
        db.execute(
            "INSERT INTO daily_metrics (date, sleep_hours, energy, mood) "
            "VALUES (?, ?, ?, ?)",
            [row["date"], row["sleep_hours"], row["energy"], row["mood"]],
        )
    counts["daily_metrics"] = len(metrics)

    return counts


if __name__ == "__main__":
    import argparse
    from ..db import DatabaseManager

    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--data-path", default="./data", help="Path to data directory")
    parser.add_argument("--days", type=int, default=14, help="Number of days of data")
    args = parser.parse_args()

    db_path = Path(args.data_path) / "unstructured.duckdb"
    db = DatabaseManager(db_path)
    db.connect()
    counts = seed_database(db, args.days)
    for table, count in counts.items():
        print(f"  {table}: {count} rows")
    print("Done!")
