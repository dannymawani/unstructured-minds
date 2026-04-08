"""Orchestrates demo data insertion into DuckDB or Postgres."""

from datetime import date
from typing import Any

from ..db.sql_compat import get_dialect, placeholder, upsert
from ..logging_config import get_logger
from .constants import DEMO_SOURCE_FILE
from .demo_data import generate_demo_data

logger = get_logger(__name__)


def seed_demo_data(db, user_id: str) -> dict[str, int]:
    """Insert demo data into all tables. Idempotent — clears existing demo rows first.

    Returns a dict of table_name → row_count inserted.
    """
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    # Clear any existing demo data for this user before seeding
    _delete_demo_rows(db, dialect, ph, user_id)

    data = generate_demo_data(today=date.today())
    counts: dict[str, int] = {}

    counts["activities"] = _insert_activities(db, dialect, ph, user_id, data["activities"])
    counts["exercise_log"] = _insert_exercise_log(db, dialect, ph, user_id, data["exercise_log"])
    counts["daily_metrics"] = _insert_daily_metrics(db, dialect, ph, user_id, data["daily_metrics"])
    counts["food_log"] = _insert_food_log(db, dialect, ph, user_id, data["food_log"])
    counts["tasks"] = _insert_tasks(db, dialect, ph, user_id, data["tasks"])

    total = sum(counts.values())
    logger.info("demo_data_seeded", user_id=user_id, total=total, **counts)
    return counts


def _delete_demo_rows(db, dialect: str, ph: str, user_id: str) -> None:
    """Delete all demo rows across all tables for this user."""
    tables = ["exercise_log", "activities", "daily_metrics", "food_log", "tasks"]
    for table in tables:
        conditions = [f"source_file = {ph}"]
        params: list[Any] = [DEMO_SOURCE_FILE]
        if dialect == "postgres":
            conditions.append(f"user_id = {ph}")
            params.append(user_id)
        db.execute(f"DELETE FROM {table} WHERE {' AND '.join(conditions)}", params)


def _insert_activities(db, dialect: str, ph: str, user_id: str, rows: list[dict]) -> int:
    cols = ["id", "date", "activity_type", "duration_minutes", "notes", "source_file"]
    if dialect == "postgres":
        cols.append("user_id")
    conflict = ["id", "user_id"] if dialect == "postgres" else ["id"]
    sql = upsert("activities", cols, conflict, dialect=dialect)

    for row in rows:
        vals: list[Any] = [row["id"], row["date"], row["activity_type"], row["duration_minutes"], row["notes"], row["source_file"]]
        if dialect == "postgres":
            vals.append(user_id)
        db.execute(sql, vals)
    return len(rows)


def _insert_exercise_log(db, dialect: str, ph: str, user_id: str, rows: list[dict]) -> int:
    cols = ["id", "activity_id", "date", "exercise_name", "weight_kg", "reps", "set_number",
            "duration_minutes", "distance_km", "notes", "source_file"]
    if dialect == "postgres":
        cols.append("user_id")
    conflict = ["id", "user_id"] if dialect == "postgres" else ["id"]
    sql = upsert("exercise_log", cols, conflict, dialect=dialect)

    for row in rows:
        vals: list[Any] = [
            row["id"], row["activity_id"], row["date"], row["exercise_name"],
            row["weight_kg"], row["reps"], row["set_number"],
            row["duration_minutes"], row["distance_km"], row["notes"], row["source_file"],
        ]
        if dialect == "postgres":
            vals.append(user_id)
        db.execute(sql, vals)
    return len(rows)


def _insert_daily_metrics(db, dialect: str, ph: str, user_id: str, rows: list[dict]) -> int:
    cols = ["date", "sleep_hours", "sleep_quality", "energy", "mood", "stress", "notes", "source_file"]
    conflict_cols = ["date"]
    if dialect == "postgres":
        cols.append("user_id")
        conflict_cols.append("user_id")
    sql = upsert("daily_metrics", cols, conflict_cols, dialect=dialect)

    for row in rows:
        vals: list[Any] = [
            row["date"], row["sleep_hours"], row["sleep_quality"],
            row["energy"], row["mood"], row["stress"], row["notes"], row["source_file"],
        ]
        if dialect == "postgres":
            vals.append(user_id)
        db.execute(sql, vals)
    return len(rows)


def _insert_food_log(db, dialect: str, ph: str, user_id: str, rows: list[dict]) -> int:
    cols = ["id", "date", "meal_type", "time", "description", "calories",
            "protein_g", "carbs_g", "fat_g", "notes", "source_file"]
    if dialect == "postgres":
        cols.append("user_id")
    placeholders = ", ".join([ph] * len(cols))
    sql = f"INSERT INTO food_log ({', '.join(cols)}) VALUES ({placeholders})"

    for row in rows:
        vals: list[Any] = [
            row["id"], row["date"], row["meal_type"], row["time"], row["description"],
            row["calories"], row["protein_g"], row["carbs_g"], row["fat_g"],
            row["notes"], row["source_file"],
        ]
        if dialect == "postgres":
            vals.append(user_id)
        db.execute(sql, vals)
    return len(rows)


def _insert_tasks(db, dialect: str, ph: str, user_id: str, rows: list[dict]) -> int:
    cols = ["id", "date", "description", "status", "completed_at", "category", "priority", "source_file"]
    if dialect == "postgres":
        cols.append("user_id")
    placeholders = ", ".join([ph] * len(cols))
    sql = f"INSERT INTO tasks ({', '.join(cols)}) VALUES ({placeholders})"

    for row in rows:
        vals: list[Any] = [
            row["id"], row["date"], row["description"], row["status"],
            row["completed_at"], row["category"], row["priority"], row["source_file"],
        ]
        if dialect == "postgres":
            vals.append(user_id)
        db.execute(sql, vals)
    return len(rows)
