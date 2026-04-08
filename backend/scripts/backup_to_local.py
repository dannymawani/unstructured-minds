#!/usr/bin/env python3
"""Pull cloud Postgres data back to local DuckDB + vault + settings.

The reverse of setup_cloud.py — restores a local environment from cloud state.

Usage:
    python -m scripts.backup_to_local                      # full backup
    python -m scripts.backup_to_local --tables-only        # data tables only
    python -m scripts.backup_to_local --vault-only         # vault files only
    python -m scripts.backup_to_local --settings-only      # JSON settings only
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import DatabaseManager
from src.db.postgres import PostgresManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from project root if DATABASE_URL not already set
if not os.getenv("DATABASE_URL"):
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                if key.strip() == "DATABASE_URL":
                    os.environ["DATABASE_URL"] = value.strip()
                    break

# Tables to pull from Postgres → DuckDB (same order as setup_cloud.py)
MIGRATE_TABLES = [
    "activities",
    "exercise_log",
    "daily_metrics",
    "food_log",
    "tasks",
    "extraction_log",
    "kanban_tasks",
    "kanban_task_updates",
    "progress_reviews",
]

# Column lists for each table (DuckDB schema — no user_id)
TABLE_COLUMNS = {
    "activities": "id, date, activity_type, duration_minutes, notes, source_file, extracted_at",
    "exercise_log": "id, activity_id, date, exercise_name, weight_kg, reps, set_number, duration_minutes, distance_km, notes, source_file, extracted_at",
    "daily_metrics": "date, sleep_hours, sleep_quality, energy, mood, stress, notes, source_file, extracted_at",
    "food_log": "id, date, meal_type, time, description, calories, protein_g, carbs_g, fat_g, notes, source_file, extracted_at",
    "tasks": "id, date, description, status, completed_at, category, priority, source_file, deadline, notes, extracted_at",
    "extraction_log": "id, file_path, file_hash, extracted_at, success, error_message",
    "kanban_tasks": "id, title, phase, priority, status, branch, depends_on, description, content, deadline, created_at, completed_at",
    "kanban_task_updates": "id, task_id, note, created_at",
    "progress_reviews": "id, period_start, period_end, key_wins, challenges, work_highlights, training_summary, personal_wins, health_metrics, goal_progress, focus_next, created_at, updated_at",
}

# Community exercises (global table, no user_id)
COMMUNITY_COLUMNS = "exercise_key, display_name, aliases, muscle_groups, category, recovery_hours, created_at"

# JSON settings keys → local filenames
JSON_SETTINGS = {
    "settings": "settings.json",
    "life_profile": "life_profile.json",
    "training_config": "training_config.json",
    "ai_exercise_cache": "ai_exercise_cache.json",
}


def backup_duckdb(duckdb_path: Path) -> None:
    """Create a timestamped safety backup of the existing DuckDB file."""
    if not duckdb_path.exists():
        print("  No existing DuckDB file — skipping safety backup")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = duckdb_path.with_suffix(f".backup_{timestamp}.duckdb")
    shutil.copy2(duckdb_path, backup_path)
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    print(f"  Backed up to {backup_path.name} ({size_mb:.1f} MB)")


def pull_tables(pg: PostgresManager, db: DatabaseManager, user_id: str) -> dict[str, int]:
    """Pull data tables from Postgres into local DuckDB."""
    counts = {}
    for table in MIGRATE_TABLES:
        columns = TABLE_COLUMNS.get(table)
        if not columns:
            continue

        col_list = [c.strip() for c in columns.split(",")]

        # Build Postgres SELECT with user_id filter
        pg_columns = columns
        try:
            rows = pg.execute(
                f"SELECT {pg_columns} FROM {table} WHERE user_id = %s",
                [user_id],
            ).fetchall()
        except Exception as e:
            print(f"  SKIP {table}: {e}")
            continue

        if not rows:
            counts[table] = 0
            continue

        # Delete existing rows in DuckDB and insert fresh
        db.execute(f"DELETE FROM {table}")

        placeholders = ", ".join(["?"] * len(col_list))
        inserted = 0
        for row in rows:
            # Convert Postgres types to DuckDB-compatible values
            values = []
            for v in row:
                if isinstance(v, dict):
                    values.append(json.dumps(v))
                elif isinstance(v, list):
                    values.append(v)
                else:
                    values.append(v)
            try:
                db.execute(
                    f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
                    values,
                )
                inserted += 1
            except Exception as e:
                print(f"  WARN {table} row: {e}")

        counts[table] = inserted

    return counts


def pull_community_exercises(pg: PostgresManager, db: DatabaseManager) -> int:
    """Pull community_exercises (global, no user_id filter)."""
    try:
        rows = pg.execute(f"SELECT {COMMUNITY_COLUMNS} FROM community_exercises").fetchall()
    except Exception as e:
        print(f"  SKIP community_exercises: {e}")
        return 0

    if not rows:
        return 0

    db.execute("DELETE FROM community_exercises")
    col_list = [c.strip() for c in COMMUNITY_COLUMNS.split(",")]
    placeholders = ", ".join(["?"] * len(col_list))

    count = 0
    for row in rows:
        values = []
        for v in row:
            if isinstance(v, (dict, list)):
                values.append(json.dumps(v))
            else:
                values.append(v)
        try:
            db.execute(
                f"INSERT OR REPLACE INTO community_exercises ({COMMUNITY_COLUMNS}) VALUES ({placeholders})",
                values,
            )
            count += 1
        except Exception as e:
            print(f"  WARN community_exercises row: {e}")

    return count


def pull_vault(pg: PostgresManager, vault_path: Path, user_id: str) -> int:
    """Pull vault_files from Postgres and write to local vault directory."""
    try:
        rows = pg.execute(
            "SELECT path, content FROM vault_files WHERE user_id = %s ORDER BY path",
            [user_id],
        ).fetchall()
    except Exception as e:
        print(f"  SKIP vault: {e}")
        return 0

    if not rows:
        return 0

    vault_path.mkdir(parents=True, exist_ok=True)
    count = 0
    for path, content in rows:
        file_path = vault_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        count += 1

    return count


def pull_settings(pg: PostgresManager, data_path: Path, user_id: str) -> int:
    """Pull user_settings from Postgres and write to local JSON files."""
    count = 0
    for key, filename in JSON_SETTINGS.items():
        try:
            row = pg.execute(
                "SELECT value FROM user_settings WHERE user_id = %s AND key = %s",
                [user_id, key],
            ).fetchone()
        except Exception as e:
            print(f"  SKIP {key}: {e}")
            continue

        if not row:
            continue

        value = row[0]
        # value comes back as dict (psycopg auto-deserializes JSONB)
        if isinstance(value, str):
            data = json.loads(value)
        else:
            data = value

        filepath = data_path / filename
        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"  {filename} <- {key}")
        count += 1

    return count


def verify_duckdb(db: DatabaseManager) -> None:
    """Print DuckDB row counts for verification."""
    all_tables = MIGRATE_TABLES + ["community_exercises"]
    for table in all_tables:
        try:
            count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"    {table}: {count} rows")
        except Exception:
            print(f"    {table}: (not found)")


def main():
    parser = argparse.ArgumentParser(description="Pull Postgres data back to local DuckDB + vault + settings")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--vault-path", type=Path, default=PROJECT_ROOT / "vault")
    parser.add_argument("--data-path", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--user-id", required=True, help="User UUID to pull data for")
    parser.add_argument("--tables-only", action="store_true", help="Only pull data tables")
    parser.add_argument("--vault-only", action="store_true", help="Only pull vault files")
    parser.add_argument("--settings-only", action="store_true", help="Only pull JSON settings")
    args = parser.parse_args()

    if not args.database_url:
        print("Error: DATABASE_URL not set. Pass --database-url or set in .env")
        sys.exit(1)

    # If no filter flags, do everything
    do_all = not (args.tables_only or args.vault_only or args.settings_only)

    duckdb_path = args.data_path / "unstructured.duckdb"
    host = args.database_url.split("@")[-1].split(":")[0] if "@" in args.database_url else "unknown"
    print(f"Source:     {host} (Postgres)")
    print(f"User ID:    {args.user_id}")
    print(f"DuckDB:     {duckdb_path}")
    print(f"Vault:      {args.vault_path}")
    print(f"Data:       {args.data_path}")
    print()

    pg = PostgresManager(args.database_url)
    pg.connect()

    try:
        # Step 1: Safety backup
        if do_all or args.tables_only:
            print("[1/6] Safety backup of DuckDB...")
            backup_duckdb(duckdb_path)
            print()

            # Step 2: Pull data tables
            print("[2/6] Pulling data tables from Postgres...")
            db = DatabaseManager(duckdb_path)
            db.connect()
            counts = pull_tables(pg, db, args.user_id)
            if counts:
                for table, n in counts.items():
                    print(f"  {table}: {n} rows")
            else:
                print("  No data pulled")
            print()

            # Step 3: Pull community exercises
            print("[3/6] Pulling community exercises...")
            ce_count = pull_community_exercises(pg, db)
            print(f"  {ce_count} exercises")
            print()
        else:
            db = None
            print("[1/6] Safety backup skipped")
            print("[2/6] Data tables skipped")
            print("[3/6] Community exercises skipped")
            print()

        # Step 4: Pull vault files
        if do_all or args.vault_only:
            print("[4/6] Pulling vault files...")
            vault_count = pull_vault(pg, args.vault_path, args.user_id)
            print(f"  {vault_count} files written")
            print()
        else:
            print("[4/6] Vault skipped")
            print()

        # Step 5: Pull JSON settings
        if do_all or args.settings_only:
            print("[5/6] Pulling JSON settings...")
            settings_count = pull_settings(pg, args.data_path, args.user_id)
            print(f"  {settings_count} settings written")
            print()
        else:
            print("[5/6] Settings skipped")
            print()

        # Step 6: Verify
        print("[6/6] Verifying local DuckDB...")
        if db is None:
            db = DatabaseManager(duckdb_path)
            db.connect()
        verify_duckdb(db)

        if db:
            db.close()

    finally:
        pg.close()

    print("\nBackup complete!")


if __name__ == "__main__":
    main()
