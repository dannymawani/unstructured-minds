#!/usr/bin/env python3
"""One-time migration: copy all data from DuckDB to Postgres (Neon).

Usage:
    cd backend
    python -m scripts.migrate_duckdb_to_postgres --user-id <UUID>

Requires:
    - DATABASE_URL env var pointing to Postgres
    - Existing DuckDB file at data/unstructured.duckdb
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path so we can import src modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import settings
from src.db.connection import DatabaseManager
from src.db.postgres import PostgresManager
from src.db.postgres_schema import init_postgres_schema

# Tables to migrate and their column mappings (DuckDB columns → same names in Postgres)
TABLES = [
    "activities",
    "exercise_log",
    "daily_metrics",
    "food_log",
    "tasks",
    "kanban_tasks",
    "kanban_task_updates",
    "progress_reviews",
    "file_index",
    "extraction_log",
]

# JSON config files to migrate to user_settings
JSON_SETTINGS = {
    "settings": "settings.json",
    "life_profile": "life_profile.json",
    "training_config": "training_config.json",
    "ai_exercise_cache": "ai_exercise_cache.json",
}


def migrate_table(duckdb: DatabaseManager, pg: PostgresManager, table: str, user_id: str) -> int:
    """Migrate a single table from DuckDB to Postgres.

    Reads all rows, adds user_id, inserts with ON CONFLICT DO NOTHING.

    Returns number of rows inserted.
    """
    try:
        result = duckdb.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
    except Exception as e:
        print(f"  WARNING: Could not read {table} from DuckDB: {e}")
        return 0

    if not rows:
        print(f"  {table}: 0 rows (empty)")
        return 0

    # Add user_id to columns
    pg_columns = ["user_id"] + columns
    placeholders = ", ".join(["%s"] * len(pg_columns))
    col_list = ", ".join(pg_columns)

    # Determine conflict columns for ON CONFLICT DO NOTHING
    # For tables with id PK, conflict on (user_id, id)
    # For daily_metrics, conflict on (user_id, date)
    # For file_index, conflict on (user_id, path)
    conflict_map = {
        "daily_metrics": "(user_id, date)",
        "file_index": "(user_id, path)",
        "extraction_log": "(id)",  # SERIAL PK
        "kanban_task_updates": "(id)",  # SERIAL PK
    }
    conflict = conflict_map.get(table, "(user_id, id)")

    inserted = 0
    for row in rows:
        try:
            pg.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT {conflict} DO NOTHING",
                [user_id] + list(row),
            )
            inserted += 1
        except Exception as e:
            print(f"  WARNING: Failed to insert row in {table}: {e}")

    return inserted


def migrate_json_settings(pg: PostgresManager, user_id: str, data_path: Path) -> int:
    """Migrate JSON config files to user_settings table."""
    migrated = 0
    for key, filename in JSON_SETTINGS.items():
        filepath = data_path / filename
        if not filepath.exists():
            print(f"  {filename}: not found, skipping")
            continue

        try:
            with open(filepath) as f:
                data = json.load(f)

            json_value = json.dumps(data, ensure_ascii=False)
            pg.execute(
                """
                INSERT INTO user_settings (user_id, key, value, updated_at)
                VALUES (%s, %s, %s::jsonb, NOW())
                ON CONFLICT (user_id, key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = NOW()
                """,
                [user_id, key, json_value],
            )
            print(f"  {filename} → user_settings['{key}']: OK")
            migrated += 1
        except Exception as e:
            print(f"  WARNING: Failed to migrate {filename}: {e}")

    return migrated


def main():
    parser = argparse.ArgumentParser(description="Migrate DuckDB data to Postgres")
    parser.add_argument("--user-id", required=True, help="User UUID to associate migrated data with")
    args = parser.parse_args()

    database_url = settings.database_url
    if not database_url:
        print("ERROR: DATABASE_URL not set. Add it to .env or set as environment variable.")
        sys.exit(1)

    duckdb_path = settings.duckdb_path
    if not duckdb_path.exists():
        print(f"ERROR: DuckDB file not found at {duckdb_path}")
        sys.exit(1)

    user_id = args.user_id
    print(f"Migration: DuckDB → Postgres")
    print(f"  DuckDB: {duckdb_path}")
    print(f"  Postgres: {database_url[:50]}...")
    print(f"  User ID: {user_id}")
    print()

    # Connect to both databases
    duckdb = DatabaseManager(duckdb_path)
    duckdb.connect()

    pg = PostgresManager(database_url)
    pg.connect()
    init_postgres_schema(pg)

    # Migrate tables
    print("=== Migrating tables ===")
    total_rows = 0
    for table in TABLES:
        count = migrate_table(duckdb, pg, table, user_id)
        total_rows += count
        print(f"  {table}: {count} rows migrated")

    # Migrate JSON settings
    print("\n=== Migrating JSON settings ===")
    settings_count = migrate_json_settings(pg, user_id, settings.data_path)

    # Summary
    print(f"\n=== Migration Complete ===")
    print(f"  Tables: {len(TABLES)}")
    print(f"  Total rows: {total_rows}")
    print(f"  JSON settings: {settings_count}")

    # Cleanup
    duckdb.close()
    pg.close()


if __name__ == "__main__":
    main()
