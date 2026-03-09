#!/usr/bin/env python3
"""One-command cloud setup: create schemas, seed vault, migrate DuckDB data, verify.

Usage:
    python -m scripts.setup_cloud                     # uses DATABASE_URL from .env
    python -m scripts.setup_cloud --database-url ...  # explicit URL
    python -m scripts.setup_cloud --drop-first        # wipe and recreate everything
    python -m scripts.setup_cloud --skip-seed         # schemas only, no vault/data seed
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.postgres import PostgresManager
from src.db.postgres_schema import init_postgres_schema

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

# Tables to migrate from DuckDB → Postgres (order matters for foreign-key-like deps)
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

# Column lists for each table (matching DuckDB schema — no user_id)
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

# JSON settings files to migrate into user_settings table
JSON_SETTINGS = {
    "settings.json": "settings",
    "training_config.json": "training_config",
    "ai_exercise_cache.json": "ai_exercise_cache",
}


def drop_all_tables(pg: PostgresManager) -> None:
    """Drop all app tables (for --drop-first)."""
    tables = [
        "vault_files", "user_settings", "custom_extractions", "extraction_log",
        "kanban_task_updates", "kanban_tasks", "progress_reviews", "file_index",
        "food_log", "tasks", "daily_metrics", "exercise_log", "activities",
    ]
    for table in tables:
        pg.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        print(f"  dropped {table}")
    print()


def seed_vault(pg: PostgresManager, vault_path: Path, user_id: str) -> int:
    """Insert all files from vault_path into vault_files table."""
    if not vault_path.is_dir():
        print(f"  Vault path not found: {vault_path} — skipping")
        return 0

    count = 0
    for file_path in sorted(vault_path.rglob("*")):
        if not file_path.is_file():
            continue
        relative = str(file_path.relative_to(vault_path))
        try:
            content = file_path.read_bytes()
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            print(f"  SKIP (binary): {relative}")
            continue

        size = len(content)
        content_hash = hashlib.sha256(content).hexdigest()
        pg.execute(
            """
            INSERT INTO vault_files (user_id, path, content, size_bytes, content_hash, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id, path) DO UPDATE
            SET content = EXCLUDED.content, size_bytes = EXCLUDED.size_bytes,
                content_hash = EXCLUDED.content_hash, updated_at = NOW()
            """,
            [user_id, relative, text, size, content_hash],
        )
        count += 1
    return count


def migrate_duckdb(pg: PostgresManager, duckdb_path: Path, user_id: str) -> dict[str, int]:
    """Migrate all data from a local DuckDB file into Postgres."""
    if not duckdb_path.exists():
        print(f"  DuckDB not found: {duckdb_path} — skipping")
        return {}

    from src.db.connection import DatabaseManager

    db = DatabaseManager(duckdb_path)
    db.connect()

    counts = {}
    for table in MIGRATE_TABLES:
        columns = TABLE_COLUMNS.get(table)
        if not columns:
            continue

        try:
            rows = db.execute(f"SELECT {columns} FROM {table}").fetchall()
        except Exception as e:
            print(f"  SKIP {table}: {e}")
            continue

        if not rows:
            counts[table] = 0
            continue

        col_list = [c.strip() for c in columns.split(",")]
        # Postgres columns include user_id
        pg_columns = "user_id, " + columns
        placeholders = ", ".join(["%s"] * (len(col_list) + 1))

        inserted = 0
        for row in rows:
            values = [user_id] + list(row)
            # Convert Python types to Postgres-compatible values
            pg_values = []
            for v in values:
                if isinstance(v, list):
                    # TEXT[] columns need Postgres array literal: {"a","b"}
                    pg_values.append(v)
                elif isinstance(v, dict):
                    pg_values.append(json.dumps(v))
                else:
                    pg_values.append(v)

            try:
                pg.execute(
                    f"INSERT INTO {table} ({pg_columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                    pg_values,
                )
                inserted += 1
            except Exception as e:
                print(f"  WARN {table} row: {e}")

        counts[table] = inserted

    db.close()
    return counts


def migrate_json_settings(pg: PostgresManager, data_path: Path, user_id: str) -> int:
    """Migrate JSON config files into user_settings table."""
    count = 0
    for filename, key in JSON_SETTINGS.items():
        filepath = data_path / filename
        if not filepath.exists():
            continue
        try:
            data = json.loads(filepath.read_text())
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
            print(f"  {key} <- {filename}")
            count += 1
        except Exception as e:
            print(f"  SKIP {filename}: {e}")
    return count


def verify(pg: PostgresManager, user_id: str) -> None:
    """Print verification summary."""
    result = pg.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
    )
    tables = [row[0] for row in result.fetchall()]
    app_tables = [t for t in tables if not t.startswith("pg_")]
    print(f"  Tables: {len(app_tables)}")

    for t in app_tables:
        try:
            count = pg.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"    {t}: {count} rows")
        except Exception:
            print(f"    {t}: (error reading)")


def main():
    parser = argparse.ArgumentParser(description="Set up cloud Postgres: schemas + data migration")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--vault-path", type=Path, default=PROJECT_ROOT / "vault")
    parser.add_argument("--data-path", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--user-id", required=True, help="User UUID to associate data with")
    parser.add_argument("--drop-first", action="store_true", help="Drop all tables before creating")
    parser.add_argument("--skip-seed", action="store_true", help="Skip vault/data seeding")
    args = parser.parse_args()

    if not args.database_url:
        print("Error: DATABASE_URL not set. Pass --database-url or set in .env")
        sys.exit(1)

    duckdb_path = args.data_path / "unstructured.duckdb"
    host = args.database_url.split("@")[-1].split(":")[0] if "@" in args.database_url else "unknown"
    print(f"Target:     {host}")
    print(f"User ID:    {args.user_id}")
    print(f"Vault:      {args.vault_path}")
    print(f"Data:       {args.data_path}")
    print(f"DuckDB:     {duckdb_path} ({'exists' if duckdb_path.exists() else 'not found'})")
    print(f"Drop first: {args.drop_first}")
    print()

    pg = PostgresManager(args.database_url)
    pg.connect()

    try:
        # Step 1: Drop
        if args.drop_first:
            print("[1/6] Dropping existing tables...")
            drop_all_tables(pg)
        else:
            print("[1/6] Drop skipped (use --drop-first to wipe)")
        print()

        # Step 2: Create schemas
        print("[2/6] Creating schemas...")
        init_postgres_schema(pg)
        print("  Done")
        print()

        if args.skip_seed:
            print("[3/6] Vault seed skipped")
            print("[4/6] DuckDB migration skipped")
            print("[5/6] JSON settings migration skipped")
        else:
            # Step 3: Seed vault
            print("[3/6] Seeding vault...")
            vault_count = seed_vault(pg, args.vault_path, args.user_id)
            print(f"  {vault_count} files seeded")
            print()

            # Step 4: Migrate DuckDB data
            print("[4/6] Migrating DuckDB data...")
            counts = migrate_duckdb(pg, duckdb_path, args.user_id)
            if counts:
                for table, n in counts.items():
                    print(f"  {table}: {n} rows")
            else:
                print("  No DuckDB data to migrate")
            print()

            # Step 5: Migrate JSON settings
            print("[5/6] Migrating JSON settings...")
            settings_count = migrate_json_settings(pg, args.data_path, args.user_id)
            print(f"  {settings_count} settings migrated")

        print()

        # Step 6: Verify
        print("[6/6] Verifying...")
        verify(pg, args.user_id)

    finally:
        pg.close()

    print("\nAll done!")


if __name__ == "__main__":
    main()
