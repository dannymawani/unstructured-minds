"""Tests for DuckDB database layer."""

from pathlib import Path

import duckdb

from src.db import DatabaseManager, get_table_names, init_database


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


class TestPostgresMigration:
    """Tests for Postgres-style DuckDB table migration."""

    @staticmethod
    def _create_postgres_style_db(db_path: Path) -> duckdb.DuckDBPyConnection:
        """Create a DuckDB file with Postgres-style schema (user_id cols, composite PKs)."""
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE activities (
                id VARCHAR NOT NULL,
                user_id UUID NOT NULL,
                date DATE NOT NULL,
                activity_type VARCHAR NOT NULL,
                duration_minutes INTEGER,
                notes VARCHAR,
                source_file VARCHAR,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, id)
            )
        """)
        conn.execute("""
            CREATE TABLE exercise_log (
                id VARCHAR NOT NULL,
                user_id UUID NOT NULL,
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
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, id)
            )
        """)
        conn.execute("""
            CREATE TABLE daily_metrics (
                user_id UUID NOT NULL,
                date DATE NOT NULL,
                sleep_hours DECIMAL(3,1),
                sleep_quality INTEGER,
                energy INTEGER,
                mood INTEGER,
                stress INTEGER,
                weight_kg DECIMAL(4,1),
                notes VARCHAR,
                source_file VARCHAR,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, date)
            )
        """)
        conn.execute("""
            CREATE TABLE food_log (
                id VARCHAR NOT NULL,
                user_id UUID NOT NULL,
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
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, id)
            )
        """)
        conn.execute("""
            CREATE TABLE tasks (
                id VARCHAR NOT NULL,
                user_id UUID NOT NULL,
                date DATE NOT NULL,
                description VARCHAR NOT NULL,
                status VARCHAR,
                completed_at TIMESTAMP,
                category VARCHAR,
                priority INTEGER,
                source_file VARCHAR,
                deadline DATE,
                notes TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, id)
            )
        """)
        conn.execute("""
            CREATE TABLE extraction_log (
                id INTEGER PRIMARY KEY,
                user_id UUID NOT NULL,
                file_path VARCHAR NOT NULL,
                file_hash VARCHAR NOT NULL,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message VARCHAR
            )
        """)
        # Also create tables that should NOT be migrated
        conn.execute("""
            CREATE TABLE kanban_tasks (
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
        conn.execute("""
            CREATE TABLE kanban_task_updates (
                id INTEGER PRIMARY KEY,
                task_id VARCHAR NOT NULL,
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE community_exercises (
                exercise_key VARCHAR PRIMARY KEY,
                display_name VARCHAR NOT NULL,
                aliases VARCHAR DEFAULT '[]',
                muscle_groups VARCHAR DEFAULT '[]',
                category VARCHAR DEFAULT 'other',
                recovery_hours INTEGER DEFAULT 48,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        return conn

    def test_migration_removes_user_id_and_adds_pks(self, tmp_path: Path) -> None:
        """Test that Postgres-style tables are migrated to correct DuckDB schema."""
        db_path = tmp_path / "pg_style.duckdb"
        conn = self._create_postgres_style_db(db_path)

        # Seed some data
        conn.execute("""
            INSERT INTO daily_metrics (user_id, date, sleep_hours, energy, mood)
            VALUES ('00000000-0000-0000-0000-000000000001', '2026-01-31', 7.5, 4, 4)
        """)
        conn.execute("""
            INSERT INTO activities (id, user_id, date, activity_type)
            VALUES ('a1', '00000000-0000-0000-0000-000000000001', '2026-01-31', 'strength')
        """)
        conn.execute("""
            INSERT INTO extraction_log (id, user_id, file_path, file_hash, success)
            VALUES (1, '00000000-0000-0000-0000-000000000001', 'test.md', 'abc123', TRUE)
        """)
        conn.close()

        # Run init_database which should trigger migration
        conn = init_database(db_path)

        # Verify user_id column is gone from migrated tables
        for table in ["daily_metrics", "activities", "exercise_log", "food_log", "tasks", "extraction_log"]:
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()]
            assert "user_id" not in cols, f"user_id should be removed from {table}"

        # Verify data was preserved
        metrics = conn.execute("SELECT sleep_hours, energy FROM daily_metrics WHERE date = '2026-01-31'").fetchone()
        assert metrics is not None
        assert float(metrics[0]) == 7.5
        assert metrics[1] == 4

        activities = conn.execute("SELECT activity_type FROM activities WHERE id = 'a1'").fetchone()
        assert activities is not None
        assert activities[0] == "strength"

        extraction = conn.execute("SELECT file_path, success FROM extraction_log WHERE file_path = 'test.md'").fetchone()
        assert extraction is not None
        assert extraction[1] is True

        # Verify INSERT OR REPLACE works (requires PK)
        conn.execute("""
            INSERT OR REPLACE INTO daily_metrics (date, sleep_hours, energy, mood)
            VALUES ('2026-01-31', 8.0, 5, 5)
        """)
        updated = conn.execute("SELECT sleep_hours FROM daily_metrics WHERE date = '2026-01-31'").fetchone()
        assert float(updated[0]) == 8.0

        # Verify no _pg_old tables remain
        table_names = get_table_names(conn)
        for t in table_names:
            assert not t.endswith("_pg_old"), f"Old table {t} should have been dropped"

        conn.close()

    def test_migration_skipped_for_correct_schema(self, tmp_path: Path) -> None:
        """Test that migration is a no-op for fresh DuckDB databases."""
        db_path = tmp_path / "fresh.duckdb"
        conn = init_database(db_path)

        # Insert data
        conn.execute("""
            INSERT INTO daily_metrics (date, sleep_hours, energy, mood)
            VALUES ('2026-01-31', 7.5, 4, 4)
        """)
        conn.close()

        # Re-run init_database — should not break anything
        conn = init_database(db_path)
        result = conn.execute("SELECT sleep_hours FROM daily_metrics WHERE date = '2026-01-31'").fetchone()
        assert float(result[0]) == 7.5
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
