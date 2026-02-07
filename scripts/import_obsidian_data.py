#!/usr/bin/env python3
"""One-time import of Obsidian CSV data into DuckDB.

Reads date-partitioned CSVs from the Obsidian repo and inserts into
the Unstructured Minds DuckDB database with column mapping.

Usage:
    python scripts/import_obsidian_data.py [--obsidian-path /path/to/obsedian]
"""

import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import duckdb

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "unstructured.duckdb"
DEFAULT_OBSIDIAN_PATH = Path("/Users/dmh/Code/obsedian")


def find_csv_files(base_dir: Path) -> list[Path]:
    """Find all CSV files recursively under a directory."""
    return sorted(base_dir.rglob("*.csv"))


def relative_source(csv_path: Path, obsidian_path: Path) -> str:
    """Get a relative source_file path for tracking."""
    return str(csv_path.relative_to(obsidian_path))


def import_exercise_log(conn: duckdb.DuckDBPyConnection, obsidian_path: Path) -> int:
    """Import exercise_log CSVs into exercise_log and activities tables."""
    csv_dir = obsidian_path / "data" / "exercise_log"
    if not csv_dir.exists():
        print("  Skipping exercise_log: directory not found")
        return 0

    files = find_csv_files(csv_dir)
    row_count = 0
    activities_seen: dict[str, dict] = {}

    for csv_path in files:
        source = relative_source(csv_path, obsidian_path)
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            set_counter: dict[str, int] = {}  # activity_id+exercise -> set number
            for row in reader:
                activity_id = row.get("activity_id", "").strip()
                exercise = row.get("exercise", "").strip()
                if not activity_id or not exercise:
                    continue

                # Track set numbers per exercise within an activity
                key = f"{activity_id}_{exercise}"
                set_counter[key] = set_counter.get(key, 0) + 1
                set_num = set_counter[key]

                # Generate unique row ID
                row_id = f"{activity_id}_{exercise}_{set_num}"

                # Parse numeric fields
                weight = float(row["weight_kg"]) if row.get("weight_kg") else None
                reps = int(row["reps"]) if row.get("reps") else None
                duration = int(row["duration_min"]) if row.get("duration_min") else None
                distance = float(row["distance_km"]) if row.get("distance_km") else None
                date = row["date"].strip()
                notes = row.get("notes", "").strip() or None

                conn.execute(
                    """INSERT OR IGNORE INTO exercise_log
                    (id, activity_id, date, exercise_name, weight_kg, reps, set_number,
                     duration_minutes, distance_km, notes, source_file, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    [row_id, activity_id, date, exercise, weight, reps, set_num,
                     duration, distance, notes, source],
                )
                row_count += 1

                # Collect activity info
                if activity_id not in activities_seen:
                    activity_type = row.get("activity_type", "other").strip()
                    activities_seen[activity_id] = {
                        "date": date,
                        "activity_type": activity_type,
                        "duration": duration,
                        "notes": notes,
                        "source": source,
                    }

    # Insert activities
    activity_count = 0
    for act_id, info in activities_seen.items():
        conn.execute(
            """INSERT OR IGNORE INTO activities
            (id, date, activity_type, duration_minutes, notes, source_file, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            [act_id, info["date"], info["activity_type"], info["duration"],
             info["notes"], info["source"]],
        )
        activity_count += 1

    print(f"  exercise_log: {row_count} rows from {len(files)} files")
    print(f"  activities: {activity_count} sessions derived from exercise_log")
    return row_count


def import_daily_metrics(conn: duckdb.DuckDBPyConnection, obsidian_path: Path) -> int:
    """Import daily_metrics CSVs.

    Column mapping:
        sleep_rating -> sleep_quality
        energy_rating -> energy
        mood_rating -> mood
    """
    csv_dir = obsidian_path / "data" / "daily_metrics"
    if not csv_dir.exists():
        print("  Skipping daily_metrics: directory not found")
        return 0

    files = find_csv_files(csv_dir)
    row_count = 0

    for csv_path in files:
        source = relative_source(csv_path, obsidian_path)
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["date"].strip()
                sleep_quality = int(row["sleep_rating"]) if row.get("sleep_rating") else None
                energy = int(row["energy_rating"]) if row.get("energy_rating") else None
                mood = int(row["mood_rating"]) if row.get("mood_rating") else None
                notes = row.get("notes", "").strip() or None

                conn.execute(
                    """INSERT OR REPLACE INTO daily_metrics
                    (date, sleep_quality, energy, mood, notes, source_file, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    [date, sleep_quality, energy, mood, notes, source],
                )
                row_count += 1

    print(f"  daily_metrics: {row_count} rows from {len(files)} files")
    return row_count


def import_food_log(conn: duckdb.DuckDBPyConnection, obsidian_path: Path) -> int:
    """Import food_log CSVs.

    Column mapping:
        meal -> meal_type
        food -> description
    """
    csv_dir = obsidian_path / "data" / "food_log"
    if not csv_dir.exists():
        print("  Skipping food_log: directory not found")
        return 0

    files = find_csv_files(csv_dir)
    row_count = 0

    for csv_path in files:
        source = relative_source(csv_path, obsidian_path)
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["date"].strip()
                meal_type = row.get("meal", "").strip() or None
                time_str = row.get("time", "").strip() or None
                description = row.get("food", "").strip() or None
                calories = int(row["calories"]) if row.get("calories") else None
                protein = int(row["protein_g"]) if row.get("protein_g") else None
                notes = row.get("notes", "").strip() or None

                # Generate unique ID from date + meal + food hash
                food_hash = hashlib.md5(
                    f"{date}_{meal_type}_{description}".encode()
                ).hexdigest()[:8]
                row_id = f"{date.replace('-', '')}_{food_hash}"

                conn.execute(
                    """INSERT OR IGNORE INTO food_log
                    (id, date, meal_type, time, description, calories, protein_g,
                     notes, source_file, extracted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    [row_id, date, meal_type, time_str, description, calories,
                     protein, notes, source],
                )
                row_count += 1

    print(f"  food_log: {row_count} rows from {len(files)} files")
    return row_count


def import_daily_tasks(conn: duckdb.DuckDBPyConnection, obsidian_path: Path) -> int:
    """Import daily_tasks CSVs.

    Column mapping:
        task_id -> id
        task -> description
        priority: text (high/medium/low) -> integer (3/2/1)

    Takes the latest status per task_id (append-only pattern).
    """
    csv_dir = obsidian_path / "data" / "daily_tasks"
    if not csv_dir.exists():
        print("  Skipping daily_tasks: directory not found")
        return 0

    files = find_csv_files(csv_dir)
    priority_map = {"high": 3, "medium": 2, "low": 1}

    # Collect all rows, then deduplicate by task_id (keep latest updated_at)
    tasks: dict[str, dict] = {}
    for csv_path in files:
        source = relative_source(csv_path, obsidian_path)
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                task_id = row.get("task_id", "").strip()
                if not task_id:
                    continue

                updated = row.get("updated_at", "").strip()
                # Keep latest version of each task
                if task_id in tasks and tasks[task_id].get("updated_at", "") >= updated:
                    continue

                status = row.get("status", "").strip() or None
                completed_at = None
                if status == "completed" and updated:
                    completed_at = updated

                priority_str = row.get("priority", "").strip().lower()
                priority = priority_map.get(priority_str)

                tasks[task_id] = {
                    "id": task_id,
                    "date": row["date"].strip(),
                    "description": row.get("task", "").strip(),
                    "status": status,
                    "completed_at": completed_at,
                    "category": row.get("category", "").strip() or None,
                    "priority": priority,
                    "source": source,
                    "updated_at": updated,
                }

    row_count = 0
    for task in tasks.values():
        conn.execute(
            """INSERT OR IGNORE INTO tasks
            (id, date, description, status, completed_at, category, priority,
             source_file, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            [task["id"], task["date"], task["description"], task["status"],
             task["completed_at"], task["category"], task["priority"], task["source"]],
        )
        row_count += 1

    print(f"  tasks: {row_count} rows (deduplicated) from {len(files)} files")
    return row_count


def main():
    obsidian_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OBSIDIAN_PATH

    if not obsidian_path.exists():
        print(f"Error: Obsidian path not found: {obsidian_path}")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"Error: DuckDB database not found: {DB_PATH}")
        print("Start the backend first to create the database schema.")
        sys.exit(1)

    print(f"Importing data from: {obsidian_path}")
    print(f"Into database: {DB_PATH}")
    print()

    conn = duckdb.connect(str(DB_PATH))

    try:
        total = 0
        total += import_exercise_log(conn, obsidian_path)
        total += import_daily_metrics(conn, obsidian_path)
        total += import_food_log(conn, obsidian_path)
        total += import_daily_tasks(conn, obsidian_path)

        print(f"\nTotal: {total} rows imported")

        # Verify
        print("\nVerification:")
        for table in ["activities", "exercise_log", "daily_metrics", "food_log", "tasks"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count} rows")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
