"""DuckDB schema definitions."""

from pathlib import Path

import duckdb


def init_database(db_path: Path | str) -> duckdb.DuckDBPyConnection:
    """Initialize DuckDB database with schema.

    Args:
        db_path: Path to database file

    Returns:
        DuckDB connection
    """
    conn = duckdb.connect(str(db_path))

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

    # Kanban task updates / notes timeline
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kanban_task_updates (
            id INTEGER PRIMARY KEY,
            task_id VARCHAR NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # File index table for fast file lookups
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_index (
            path VARCHAR PRIMARY KEY,
            filename VARCHAR NOT NULL,
            extension VARCHAR,
            size_bytes BIGINT,
            modified_at TIMESTAMP,
            content_hash VARCHAR
        )
    """)

    # Extraction log table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extraction_log (
            id INTEGER PRIMARY KEY,
            file_path VARCHAR NOT NULL,
            file_hash VARCHAR NOT NULL,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN,
            error_message VARCHAR
        )
    """)

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

    # Index on file_index for file search
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_index_filename
        ON file_index(filename)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_file_index_extension
        ON file_index(extension)
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
