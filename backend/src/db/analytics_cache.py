"""Analytics cache: populates an in-memory DuckDB from Postgres for fast analytics queries.

The DuckDB instance is disposable — it is rebuilt from Postgres on startup
and refreshed periodically in the background.
"""

import asyncio

from ..logging_config import get_logger
from .connection import DatabaseManager

logger = get_logger(__name__)

# Tables to cache from Postgres into DuckDB for analytics
CACHE_TABLES = [
    "activities",
    "exercise_log",
    "daily_metrics",
    "food_log",
    "tasks",
    "extraction_log",
    "kanban_tasks",
    "kanban_task_updates",
]

# DuckDB CREATE TABLE statements for the cache (no user_id — single-user local cache)
_DUCKDB_CACHE_SCHEMA = {
    "activities": """
        CREATE TABLE IF NOT EXISTS activities (
            id VARCHAR PRIMARY KEY,
            date DATE NOT NULL,
            activity_type VARCHAR NOT NULL,
            duration_minutes INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "exercise_log": """
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
    """,
    "daily_metrics": """
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
    """,
    "food_log": """
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
    """,
    "tasks": """
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
    """,
    "extraction_log": """
        CREATE SEQUENCE IF NOT EXISTS extraction_log_id_seq;
        CREATE TABLE IF NOT EXISTS extraction_log (
            id INTEGER PRIMARY KEY DEFAULT nextval('extraction_log_id_seq'),
            file_path VARCHAR NOT NULL,
            file_hash VARCHAR NOT NULL,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN,
            error_message VARCHAR
        )
    """,
    "kanban_tasks": """
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
    """,
    "kanban_task_updates": """
        CREATE TABLE IF NOT EXISTS kanban_task_updates (
            id INTEGER PRIMARY KEY,
            task_id VARCHAR NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
}

# Columns to SELECT from Postgres for each table (excludes user_id)
_PG_SELECT_COLUMNS = {
    "activities": "id, date, activity_type, duration_minutes, notes, source_file, extracted_at",
    "exercise_log": "id, activity_id, date, exercise_name, weight_kg, reps, set_number, duration_minutes, distance_km, notes, source_file, extracted_at",
    "daily_metrics": "date, sleep_hours, sleep_quality, energy, mood, stress, weight_kg, notes, source_file, extracted_at",
    "food_log": "id, date, meal_type, time, description, calories, protein_g, carbs_g, fat_g, notes, source_file, extracted_at",
    "tasks": "id, date, description, status, completed_at, category, priority, source_file, deadline, notes, extracted_at",
    "extraction_log": "id, file_path, file_hash, extracted_at, success, error_message",
    "kanban_tasks": "id, title, phase, priority, status, branch, depends_on, description, content, deadline, created_at, completed_at",
    "kanban_task_updates": "id, task_id, note, created_at",
}


class AnalyticsCacheManager:
    """Refreshes an in-memory DuckDB from Postgres for analytics queries."""

    def __init__(self, pg, duckdb: DatabaseManager) -> None:
        self._pg = pg
        self._duckdb = duckdb
        self._user_id: str | None = None
        self._refresh_task: asyncio.Task | None = None

    def init_cache_schema(self) -> None:
        """Create DuckDB tables for the analytics cache."""
        for table, ddl in _DUCKDB_CACHE_SCHEMA.items():
            for stmt in ddl.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    self._duckdb.execute(stmt)

    def refresh(self, user_id: str | None = None) -> None:
        """Full refresh: read from Postgres, write to DuckDB.

        Clears and repopulates each cached table.
        If user_id is passed, updates the stored user. Skips if no user set.
        """
        if user_id is not None:
            self._user_id = user_id
        if self._user_id is None:
            logger.debug("cache_refresh_skipped_no_user")
            return
        for table in CACHE_TABLES:
            try:
                columns = _PG_SELECT_COLUMNS.get(table)
                if not columns:
                    continue

                # Read from Postgres
                rows = self._pg.execute(
                    f"SELECT {columns} FROM {table} WHERE user_id = %s",
                    [self._user_id],
                ).fetchall()

                # Clear DuckDB table
                self._duckdb.execute(f"DELETE FROM {table}")

                if not rows:
                    continue

                # Insert into DuckDB
                col_count = len(columns.split(","))
                placeholders = ", ".join(["?"] * col_count)
                col_list = columns.strip()
                insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

                for row in rows:
                    self._duckdb.execute(insert_sql, list(row))

                logger.debug("cache_refreshed", table=table, rows=len(rows))

            except Exception as e:
                logger.warning("cache_refresh_failed", table=table, error=str(e))

        logger.info("analytics_cache_refresh_complete")

    async def _periodic_refresh(self, interval: int = 60) -> None:
        """Background refresh loop. Skips iterations until a user is set."""
        while True:
            await asyncio.sleep(interval)
            if self._user_id is None:
                continue
            try:
                self.refresh()
            except Exception as e:
                logger.warning("periodic_cache_refresh_failed", error=str(e))

    def start_background_refresh(self, interval: int = 60) -> None:
        """Start periodic background cache refresh."""
        self._refresh_task = asyncio.create_task(self._periodic_refresh(interval))
        logger.info("analytics_cache_background_refresh_started", interval=interval)

    async def stop(self) -> None:
        """Stop the background refresh."""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            logger.info("analytics_cache_background_refresh_stopped")
