"""Tests for onboarding / demo data system."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_settings(tmp_path: Path):
    """Create test settings with temp paths."""
    with patch("src.config.Settings"):
        mock_settings = MagicMock()
        mock_settings.vault_path = tmp_path / "vault"
        mock_settings.data_path = tmp_path / "data"
        mock_settings.duckdb_path = tmp_path / "data" / "test.duckdb"
        mock_settings.host = "0.0.0.0"
        mock_settings.port = 8000
        mock_settings.debug = False
        mock_settings.anthropic_api_key = None
        mock_settings.claude_enabled = False
        mock_settings.database_url = None
        mock_settings.is_cloud_mode = False

        mock_settings.vault_path.mkdir(parents=True, exist_ok=True)
        mock_settings.data_path.mkdir(parents=True, exist_ok=True)

        with patch("src.main.settings", mock_settings), \
             patch("src.api.onboarding.settings", mock_settings):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def db(client):
    """Get database from app state."""
    from src.main import app
    return app.state.db


# ── Unit tests: demo data generation ─────────────────────────────────────────


class TestDemoDataGeneration:
    def test_generates_all_tables(self):
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        assert "activities" in data
        assert "exercise_log" in data
        assert "daily_metrics" in data
        assert "food_log" in data
        assert "tasks" in data

    def test_daily_metrics_count(self):
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        assert len(data["daily_metrics"]) == 30

    def test_all_records_have_demo_source_file(self):
        from src.onboarding.constants import DEMO_SOURCE_FILE
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        for table, rows in data.items():
            for row in rows:
                assert row["source_file"] == DEMO_SOURCE_FILE, f"{table} row missing demo source_file"

    def test_deterministic_output(self):
        from src.onboarding.demo_data import generate_demo_data

        d = date(2026, 2, 16)
        data1 = generate_demo_data(today=d)
        data2 = generate_demo_data(today=d)

        for table in data1:
            assert len(data1[table]) == len(data2[table])
            for r1, r2 in zip(data1[table], data2[table]):
                assert r1 == r2

    def test_activities_reasonable_count(self):
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        # ~4 strength days/month + ~4 BJJ days/month + some cardio
        assert len(data["activities"]) >= 8
        assert len(data["activities"]) <= 30

    def test_exercise_log_has_progressive_weights(self):
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        # Filter to a single exercise
        squats = [r for r in data["exercise_log"] if r["exercise_name"] == "squat"]
        if len(squats) >= 6:
            first_weights = [r["weight_kg"] for r in squats[:3]]
            last_weights = [r["weight_kg"] for r in squats[-3:]]
            assert max(last_weights) >= max(first_weights)

    def test_tasks_status_distribution(self):
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        statuses = [t["status"] for t in data["tasks"]]
        assert "done" in statuses
        assert "backlog" in statuses
        assert "in_progress" in statuses
        assert "cancelled" in statuses

    def test_task_ids_prefixed(self):
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        for task in data["tasks"]:
            assert task["id"].startswith("demo_")

    def test_food_log_reasonable_count(self):
        from src.onboarding.demo_data import generate_demo_data

        data = generate_demo_data(today=date(2026, 2, 16))
        # ~15 days tracked, 2-3 meals each
        assert len(data["food_log"]) >= 15
        assert len(data["food_log"]) <= 60


# ── Integration tests: seed + lifecycle ──────────────────────────────────────


class TestSeedAndLifecycle:
    def test_seed_inserts_data(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.seed import seed_demo_data

        counts = seed_demo_data(db, LOCAL_USER_ID)
        assert counts["daily_metrics"] == 30
        assert counts["activities"] > 0
        assert counts["exercise_log"] > 0
        assert counts["tasks"] == 20

        # Verify data is in DB
        result = db.execute("SELECT COUNT(*) FROM daily_metrics WHERE source_file = '__demo__'").fetchone()
        assert result[0] == 30

    def test_seed_is_idempotent(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.seed import seed_demo_data

        counts1 = seed_demo_data(db, LOCAL_USER_ID)
        counts2 = seed_demo_data(db, LOCAL_USER_ID)

        # Should have same counts (clears and re-inserts)
        assert counts1 == counts2

        # Should not have double data
        result = db.execute("SELECT COUNT(*) FROM daily_metrics WHERE source_file = '__demo__'").fetchone()
        assert result[0] == 30

    def test_clear_all_demo_data(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.lifecycle import clear_all_demo_data
        from src.onboarding.seed import seed_demo_data

        seed_demo_data(db, LOCAL_USER_ID)
        deleted = clear_all_demo_data(db, LOCAL_USER_ID)
        assert deleted > 0

        # Verify all demo data is gone
        for table in ["activities", "exercise_log", "daily_metrics", "food_log", "tasks"]:
            result = db.execute(f"SELECT COUNT(*) FROM {table} WHERE source_file = '__demo__'").fetchone()
            assert result[0] == 0, f"Demo data still in {table}"

    def test_cleanup_demo_for_date(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.lifecycle import cleanup_demo_for_date
        from src.onboarding.seed import seed_demo_data

        seed_demo_data(db, LOCAL_USER_ID)

        today = date.today()
        target = (today - timedelta(days=15)).isoformat()

        deleted = cleanup_demo_for_date(db, target, LOCAL_USER_ID)
        # Should have deleted at least the daily_metrics row for that date
        assert deleted >= 1

        # Other dates should still have data
        result = db.execute("SELECT COUNT(*) FROM daily_metrics WHERE source_file = '__demo__'").fetchone()
        assert result[0] == 29  # 30 - 1

    def test_get_demo_data_count(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.lifecycle import get_demo_data_count
        from src.onboarding.seed import seed_demo_data

        assert get_demo_data_count(db, LOCAL_USER_ID) == 0
        seed_demo_data(db, LOCAL_USER_ID)
        assert get_demo_data_count(db, LOCAL_USER_ID) > 0

    def test_get_real_data_count(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.lifecycle import get_real_data_count

        assert get_real_data_count(db, LOCAL_USER_ID) == 0

        # Insert real data
        db.execute(
            "INSERT INTO daily_metrics (date, sleep_hours, source_file) VALUES (?, ?, ?)",
            [date.today().isoformat(), 7.5, "Daily-Notes/2026-02/2026-02-16.md"],
        )
        assert get_real_data_count(db, LOCAL_USER_ID) == 1

    def test_check_graduation_below_threshold(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.lifecycle import check_graduation

        assert check_graduation(db, LOCAL_USER_ID) is False

    def test_check_graduation_above_threshold(self, db):
        from src.config import LOCAL_USER_ID
        from src.onboarding.lifecycle import check_graduation

        # Insert 7+ real daily notes
        today = date.today()
        for i in range(8):
            d = (today - timedelta(days=i)).isoformat()
            db.execute(
                "INSERT OR REPLACE INTO daily_metrics (date, sleep_hours, source_file) VALUES (?, ?, ?)",
                [d, 7.5, f"Daily-Notes/2026-02/{d}.md"],
            )

        assert check_graduation(db, LOCAL_USER_ID) is True


# ── API endpoint tests ───────────────────────────────────────────────────────


class TestOnboardingAPI:
    def test_status_new_user(self, client):
        resp = client.get("/onboarding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_new_user"] is True
        assert data["demo_active"] is False
        assert data["demo_data_count"] == 0
        assert data["real_data_count"] == 0

    def test_seed_demo_data(self, client):
        resp = client.post("/onboarding/seed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rows_inserted"]["daily_metrics"] == 30
        assert data["rows_inserted"]["tasks"] == 20

    def test_status_after_seed(self, client):
        client.post("/onboarding/seed")
        resp = client.get("/onboarding/status")
        data = resp.json()
        assert data["is_new_user"] is False
        assert data["demo_active"] is True
        assert data["demo_data_count"] > 0

    def test_clear_demo_data(self, client):
        client.post("/onboarding/seed")
        resp = client.post("/onboarding/clear-demo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rows_deleted"] > 0

        # Verify demo data is gone
        status = client.get("/onboarding/status").json()
        assert status["demo_active"] is False
        assert status["demo_data_count"] == 0

    def test_complete_onboarding(self, client):
        resp = client.post("/onboarding/complete")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        status = client.get("/onboarding/status").json()
        assert status["onboarding_completed"] is True
        assert status["is_new_user"] is False

    def test_seed_idempotent(self, client):
        client.post("/onboarding/seed")
        resp = client.post("/onboarding/seed")
        assert resp.status_code == 200

        # Should still have exactly 30 metrics rows
        status = client.get("/onboarding/status").json()
        assert status["demo_active"] is True
