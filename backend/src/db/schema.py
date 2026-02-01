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

    return conn


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
