"""Tests for DuckDB database layer."""

import pytest
from pathlib import Path

from src.db import DatabaseManager, init_database, get_table_names


class TestSchema:
    """Tests for database schema."""

    def test_schema_creation(self, tmp_path: Path) -> None:
        """Test that all tables are created."""
        db_path = tmp_path / "test.duckdb"
        conn = init_database(db_path)

        table_names = get_table_names(conn)

        expected_tables = [
            "activities",
            "exercise_log",
            "daily_metrics",
            "food_log",
            "tasks",
            "extraction_log",
        ]
        for table in expected_tables:
            assert table in table_names, f"Table {table} not found"

        conn.close()

    def test_insert_and_query_exercise_log(self, tmp_path: Path) -> None:
        """Test inserting and querying exercise_log."""
        db_path = tmp_path / "test.duckdb"
        conn = init_database(db_path)

        conn.execute("""
            INSERT INTO exercise_log (id, activity_id, date, exercise_name, weight_kg, reps, set_number)
            VALUES ('20260131_str_1_squat_1', '20260131_str_1', '2026-01-31', 'squat', 100.0, 5, 1)
        """)

        result = conn.execute("SELECT exercise_name, weight_kg FROM exercise_log").fetchone()
        assert result[0] == "squat"
        assert float(result[1]) == 100.0

        conn.close()

    def test_insert_and_query_activities(self, tmp_path: Path) -> None:
        """Test inserting and querying activities."""
        db_path = tmp_path / "test.duckdb"
        conn = init_database(db_path)

        conn.execute("""
            INSERT INTO activities (id, date, activity_type, duration_minutes)
            VALUES ('20260131_str_1', '2026-01-31', 'strength', 60)
        """)

        result = conn.execute("SELECT activity_type, duration_minutes FROM activities").fetchone()
        assert result[0] == "strength"
        assert result[1] == 60

        conn.close()

    def test_insert_and_query_daily_metrics(self, tmp_path: Path) -> None:
        """Test inserting and querying daily_metrics."""
        db_path = tmp_path / "test.duckdb"
        conn = init_database(db_path)

        conn.execute("""
            INSERT INTO daily_metrics (date, sleep_hours, energy, mood)
            VALUES ('2026-01-31', 7.5, 4, 4)
        """)

        result = conn.execute("SELECT sleep_hours, energy FROM daily_metrics").fetchone()
        assert float(result[0]) == 7.5
        assert result[1] == 4

        conn.close()


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    def test_connect_creates_database(self, tmp_path: Path) -> None:
        """Test that connect creates database file."""
        db_path = tmp_path / "new.duckdb"
        assert not db_path.exists()

        with DatabaseManager(db_path) as db:
            db.execute("SELECT 1")

        assert db_path.exists()

    def test_execute_query(self, tmp_path: Path) -> None:
        """Test executing queries through manager."""
        db_path = tmp_path / "test.duckdb"

        with DatabaseManager(db_path) as db:
            db.execute("""
                INSERT INTO activities (id, date, activity_type)
                VALUES ('test_1', '2026-01-31', 'test')
            """)

            result = db.execute("SELECT COUNT(*) FROM activities").fetchone()
            assert result[0] == 1

    def test_context_manager_closes_connection(self, tmp_path: Path) -> None:
        """Test that context manager closes connection."""
        db_path = tmp_path / "test.duckdb"
        db = DatabaseManager(db_path)

        with db:
            assert db._conn is not None

        assert db._conn is None
