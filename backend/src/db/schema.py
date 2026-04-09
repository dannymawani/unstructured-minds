"""DuckDB schema definitions."""

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

# Tables that need migration from Postgres-style schema (with user_id) to DuckDB schema.
_PG_MIGRATION_TABLES = [
    "daily_metrics", "activities", "exercise_log", "food_log", "tasks", "extraction_log",
]

# All known index names (DuckDB + Postgres) that may exist on affected tables.
_ALL_INDEX_NAMES = [
    # DuckDB indexes from _create_indexes()
    "idx_exercise_date", "idx_metrics_date", "idx_extraction_path", "idx_food_date",
    "idx_tasks_date", "idx_tasks_status", "idx_kanban_status", "idx_kanban_phase",
    "idx_activities_date", "idx_activities_type", "idx_exercise_name_date",
    "idx_tasks_date_status", "idx_activities_date_type", "idx_food_date_type",
    # Postgres indexes that may have been created in DuckDB file
    "idx_pg_exercise_date", "idx_pg_metrics_date", "idx_pg_extraction_path",
    "idx_pg_food_date", "idx_pg_tasks_date", "idx_pg_tasks_status",
    "idx_pg_kanban_status", "idx_pg_kanban_phase", "idx_pg_activities_date",
    "idx_pg_activities_type", "idx_pg_kanban_updates_task", "idx_pg_vault_files_updated",
    "idx_pg_exercise_name_date", "idx_pg_tasks_date_status",
    "idx_pg_activities_date_type", "idx_pg_food_date_type",
]

# Column lists for copying data from Postgres-style tables (excludes user_id).
_PG_MIGRATION_COLUMNS = {
    "daily_metrics": "date, sleep_hours, sleep_quality, energy, mood, stress, weight_kg, notes, source_file, extracted_at",
    "activities": "id, date, activity_type, duration_minutes, notes, source_file, extracted_at",
    "exercise_log": "id, activity_id, date, exercise_name, weight_kg, reps, set_number, duration_minutes, distance_km, notes, source_file, extracted_at",
    "food_log": "id, date, meal_type, time, description, calories, protein_g, carbs_g, fat_g, notes, source_file, extracted_at",
    "tasks": "id, date, description, status, completed_at, category, priority, source_file, deadline, notes, extracted_at",
    # extraction_log: omit id (let sequence assign) and user_id
    "extraction_log": "file_path, file_hash, extracted_at, success, error_message",
}


def _prepare_postgres_migration(conn: duckdb.DuckDBPyConnection) -> bool:
    """Detect and prepare migration from Postgres-style DuckDB tables.

    If the DuckDB file was originally created under Postgres mode, tables
    will have user_id columns and composite/missing primary keys. This
    function renames those tables so the normal CREATE TABLE IF NOT EXISTS
    statements can recreate them with correct single-column PKs.

    Returns True if migration is needed (tables were renamed).
    """
    # Detection: check if daily_metrics exists and has a user_id column
    try:
        rows = conn.execute("PRAGMA table_info('daily_metrics')").fetchall()
    except duckdb.CatalogException:
        return False  # Table doesn't exist yet (fresh database)
    if not rows:
        return False
    cols = [row[1] for row in rows]
    if "user_id" not in cols:
        return False  # Already has correct DuckDB schema

    logger.info("Detected Postgres-style DuckDB tables — starting migration")

    # Drop all known indexes so renamed tables don't hold stale index names
    for idx in _ALL_INDEX_NAMES:
        conn.execute(f"DROP INDEX IF EXISTS {idx}")

    # Rename affected tables
    for table in _PG_MIGRATION_TABLES:
        conn.execute(f"ALTER TABLE {table} RENAME TO {table}_pg_old")

    # Drop sequence so it gets recreated fresh
    conn.execute("DROP SEQUENCE IF EXISTS extraction_log_id_seq")

    return True


def _finish_postgres_migration(conn: duckdb.DuckDBPyConnection) -> None:
    """Copy data from renamed Postgres-style tables and drop them."""
    for table in _PG_MIGRATION_TABLES:
        cols = _PG_MIGRATION_COLUMNS[table]
        conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {table}_pg_old")
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        conn.execute(f"DROP TABLE {table}_pg_old")
        logger.info("Migrated table %s (%d rows)", table, count)

    logger.info("Postgres-to-DuckDB migration complete")


def init_database(db_path: Path | str) -> duckdb.DuckDBPyConnection:
    """Initialize DuckDB database with schema.

    Args:
        db_path: Path to database file

    Returns:
        DuckDB connection
    """
    conn = duckdb.connect(str(db_path))

    # Phase 1: Detect and prepare Postgres-style table migration
    migrating = _prepare_postgres_migration(conn)

    # Activities table (workouts, sessions)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            activity_type VARCHAR NOT NULL,
            duration_minutes INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Exercise log table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS exercise_log (
            id VARCHAR PRIMARY KEY,
            activity_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            exercise_name VARCHAR NOT NULL,
            weight_kg DECIMAL(5,1),
            reps INTEGER,
            set_number INTEGER,
            duration_minutes INTEGER,
            distance_km DECIMAL(5,2),
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Daily metrics table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_metrics (
            date DATE PRIMARY KEY,
            sleep_hours DECIMAL(3,1),
            sleep_quality INTEGER,
            energy INTEGER,
            mood INTEGER,
            stress INTEGER,
            weight_kg DECIMAL(4,1),
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Food log table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_log (
            id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            meal_type VARCHAR,
            time TIME,
            description VARCHAR,
            calories INTEGER,
            protein_g INTEGER,
            carbs_g INTEGER,
            fat_g INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tasks table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            description VARCHAR NOT NULL,
            status VARCHAR,
            completed_at TIMESTAMP,
            category VARCHAR,
            priority INTEGER,
            source_file VARCHAR,
            deadline DATE,
            notes TEXT,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Kanban tasks table (dev planning tasks)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kanban_tasks (
            id VARCHAR PRIMARY KEY,
            title VARCHAR NOT NULL,
            phase VARCHAR,
            priority VARCHAR,
            status VARCHAR NOT NULL DEFAULT 'not_started',
            branch VARCHAR,
            depends_on VARCHAR,
            description VARCHAR,
            content TEXT,
            deadline DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Migration: add deadline column if missing (existing databases)
    try:
        conn.execute("SELECT deadline FROM kanban_tasks LIMIT 0")
    except duckdb.BinderException:
        conn.execute("ALTER TABLE kanban_tasks ADD COLUMN deadline DATE")

    # Migration: add deadline column to personal tasks if missing
    try:
        conn.execute("SELECT deadline FROM tasks LIMIT 0")
    except duckdb.BinderException:
        conn.execute("ALTER TABLE tasks ADD COLUMN deadline DATE")

    # Migration: add notes column to personal tasks if missing
    try:
        conn.execute("SELECT notes FROM tasks LIMIT 0")
    except duckdb.BinderException:
        conn.execute("ALTER TABLE tasks ADD COLUMN notes TEXT")

    # Migration: add weight_kg column to daily_metrics if missing
    try:
        conn.execute("SELECT weight_kg FROM daily_metrics LIMIT 0")
    except duckdb.BinderException:
        conn.execute("ALTER TABLE daily_metrics ADD COLUMN weight_kg DECIMAL(4,1)")

    # Migration: normalize task statuses to new kanban values
    conn.execute("UPDATE tasks SET status = 'backlog' WHERE status IN ('pending', 'todo')")
    conn.execute("UPDATE tasks SET status = 'done' WHERE status = 'completed'")
    conn.execute("UPDATE tasks SET status = 'in_progress' WHERE status = 'rolled_over'")
    # Backfill completed_at for done/cancelled tasks that don't already have one
    conn.execute("""
        UPDATE tasks SET completed_at = CAST(date AS TIMESTAMP)
        WHERE status IN ('done', 'cancelled') AND completed_at IS NULL
    """)

    # Migration: deduplicate tasks — keep oldest per (source_file, description),
    # delete newer duplicates
    conn.execute("""
        DELETE FROM tasks
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY source_file, description
                           ORDER BY extracted_at ASC, id ASC
                       ) AS rn
                FROM tasks
                WHERE source_file IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
    """)

    # Kanban task updates / notes timeline
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kanban_task_updates (
            id INTEGER PRIMARY KEY,
            task_id VARCHAR NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Community exercises table (shared anonymous exercise contributions)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS community_exercises (
            exercise_key VARCHAR PRIMARY KEY,
            display_name VARCHAR NOT NULL,
            aliases VARCHAR DEFAULT '[]',
            muscle_groups VARCHAR DEFAULT '[]',
            category VARCHAR DEFAULT 'other',
            recovery_hours INTEGER DEFAULT 48,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Extraction log table
    conn.execute("CREATE SEQUENCE IF NOT EXISTS extraction_log_id_seq")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extraction_log (
            id INTEGER PRIMARY KEY DEFAULT nextval('extraction_log_id_seq'),
            file_path VARCHAR NOT NULL,
            file_hash VARCHAR NOT NULL,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN,
            error_message VARCHAR
        )
    """)

    # Phase 2: Complete Postgres migration — copy data, drop old tables
    if migrating:
        _finish_postgres_migration(conn)

    # Create indexes for performance optimization
    # These significantly speed up common queries on large datasets
    _create_indexes(conn)

    return conn


def _create_indexes(conn: duckdb.DuckDBPyConnection) -> None:
    """Create database indexes for query performance.

    DuckDB uses these indexes to speed up:
    - Date-based filtering for dashboard queries
    - File path lookups for extraction tracking
    - Activity joins and lookups

    Args:
        conn: DuckDB connection
    """
    # Index on exercise_log date for time-range queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_exercise_date
        ON exercise_log(date)
    """)

    # Index on daily_metrics date for dashboard queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metrics_date
        ON daily_metrics(date)
    """)

    # Index on extraction_log file_path for tracking processed files
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_extraction_path
        ON extraction_log(file_path)
    """)

    # Index on food_log date for nutrition queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_date
        ON food_log(date)
    """)

    # Index on tasks date and status for kanban/task views
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_date
        ON tasks(date)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_status
        ON tasks(status)
    """)

    # Index on kanban_tasks for board queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_kanban_status
        ON kanban_tasks(status)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_kanban_phase
        ON kanban_tasks(phase)
    """)

    # Index on activities for dashboard queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_date
        ON activities(date)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_type
        ON activities(activity_type)
    """)

    # Composite indexes for common query patterns
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_exercise_name_date
        ON exercise_log(exercise_name, date)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_date_status
        ON tasks(date, status)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_date_type
        ON activities(date, activity_type)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_date_type
        ON food_log(date, meal_type)
    """)


def get_table_names(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Get list of table names in database.

    Args:
        conn: DuckDB connection

    Returns:
        List of table names
    """
    result = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
    """).fetchall()
    return [row[0] for row in result]
