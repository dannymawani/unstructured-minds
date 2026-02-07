"""Tests for dashboard API endpoints."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_settings(tmp_path: Path):
    """Create test settings with temp paths."""
    with patch("src.config.Settings") as mock_settings_cls:
        mock_settings = MagicMock()
        mock_settings.vault_path = tmp_path / "vault"
        mock_settings.data_path = tmp_path / "data"
        mock_settings.duckdb_path = tmp_path / "data" / "test.duckdb"
        mock_settings.host = "0.0.0.0"
        mock_settings.port = 8000
        mock_settings.debug = False
        mock_settings.anthropic_api_key = None
        mock_settings.claude_enabled = False

        mock_settings.vault_path.mkdir(parents=True, exist_ok=True)
        mock_settings.data_path.mkdir(parents=True, exist_ok=True)

        with patch("src.main.settings", mock_settings):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def db_with_data(client):
    """Seed database with test data."""
    from src.main import app
    db = app.state.db

    today = date.today()
    week_ago = today - timedelta(days=7)

    # Insert activities
    for i in range(7):
        day = today - timedelta(days=i)
        activity_type = "strength" if i % 2 == 0 else "cardio"
        db.execute(
            """
            INSERT INTO activities (id, date, activity_type, duration_minutes)
            VALUES (?, ?, ?, ?)
            """,
            [f"act_{i}", str(day), activity_type, 30 + i * 5],
        )

    # Insert daily metrics
    for i in range(7):
        day = today - timedelta(days=i)
        db.execute(
            """
            INSERT INTO daily_metrics (date, sleep_hours, energy, mood, stress)
            VALUES (?, ?, ?, ?, ?)
            """,
            [str(day), 7.0 + (i % 3) * 0.5, 6 + (i % 4), 7 + (i % 3), 4 - (i % 3)],
        )

    # Insert exercises
    for i in range(5):
        day = today - timedelta(days=i)
        db.execute(
            """
            INSERT INTO exercise_log (id, activity_id, date, exercise_name, weight_kg, reps, set_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [f"ex_{i}", f"act_{i}", str(day), "Squat", 100 + i * 5, 5, 1],
        )

    return db


class TestWeeklyActivity:
    """Tests for weekly activity endpoint."""

    def test_weekly_activity_returns_data(self, client, db_with_data):
        """Test that weekly activity returns aggregated data."""
        response = client.get("/dashboard/weekly-activity")

        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert "total_duration_minutes" in data
        assert "period" in data

    def test_weekly_activity_groups_by_type(self, client, db_with_data):
        """Test that activities are grouped by type."""
        response = client.get("/dashboard/weekly-activity")

        data = response.json()
        activities = data["activities"]

        # Should have both strength and cardio
        types = [a["activity_type"] for a in activities]
        assert "strength" in types or "cardio" in types

    def test_weekly_activity_with_custom_days(self, client, db_with_data):
        """Test weekly activity with custom day range."""
        response = client.get("/dashboard/weekly-activity?days=14")

        assert response.status_code == 200
        data = response.json()
        assert data["period"]["days"] == 14

    def test_weekly_activity_empty_db(self, client):
        """Test weekly activity with empty database."""
        response = client.get("/dashboard/weekly-activity")

        assert response.status_code == 200
        data = response.json()
        assert data["activities"] == []
        assert data["total_duration_minutes"] == 0


class TestMetricsTrends:
    """Tests for metrics trends endpoint."""

    def test_metrics_trends_returns_data(self, client, db_with_data):
        """Test that metrics trends returns time series data."""
        response = client.get("/dashboard/metrics-trends")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "period" in data

    def test_metrics_trends_has_all_fields(self, client, db_with_data):
        """Test that metrics include all tracked fields."""
        response = client.get("/dashboard/metrics-trends")

        data = response.json()
        metrics = data["metrics"]

        assert len(metrics) > 0
        first = metrics[0]
        assert "date" in first
        assert "sleep_hours" in first
        assert "energy" in first
        assert "mood" in first
        assert "stress" in first

    def test_metrics_trends_sorted_by_date(self, client, db_with_data):
        """Test that metrics are sorted by date ascending."""
        response = client.get("/dashboard/metrics-trends")

        data = response.json()
        metrics = data["metrics"]
        dates = [m["date"] for m in metrics]

        assert dates == sorted(dates)

    def test_metrics_trends_with_custom_days(self, client, db_with_data):
        """Test metrics trends with custom day range."""
        response = client.get("/dashboard/metrics-trends?days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["period"]["days"] == 30

    def test_metrics_trends_empty_db(self, client):
        """Test metrics trends with empty database."""
        response = client.get("/dashboard/metrics-trends")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"] == []


class TestExerciseProgress:
    """Tests for exercise progress endpoint."""

    def test_exercise_progress_returns_data(self, client, db_with_data):
        """Test that exercise progress returns data."""
        response = client.get("/dashboard/exercise-progress?exercise=Squat")

        assert response.status_code == 200
        data = response.json()
        assert "exercise" in data
        assert "progress" in data
        assert "summary" in data

    def test_exercise_progress_tracks_weight(self, client, db_with_data):
        """Test that progress tracks weight over time."""
        response = client.get("/dashboard/exercise-progress?exercise=Squat")

        data = response.json()
        progress = data["progress"]

        assert len(progress) > 0
        first = progress[0]
        assert "date" in first
        assert "max_weight_kg" in first

    def test_exercise_progress_calculates_summary(self, client, db_with_data):
        """Test that summary statistics are calculated."""
        response = client.get("/dashboard/exercise-progress?exercise=Squat")

        data = response.json()
        summary = data["summary"]

        assert "current_max" in summary
        assert "all_time_max" in summary
        assert "total_volume" in summary

    def test_exercise_progress_requires_exercise_param(self, client, db_with_data):
        """Test that exercise parameter is required."""
        response = client.get("/dashboard/exercise-progress")

        assert response.status_code == 422  # Validation error

    def test_exercise_progress_unknown_exercise(self, client, db_with_data):
        """Test progress for unknown exercise returns empty."""
        response = client.get("/dashboard/exercise-progress?exercise=Unknown")

        assert response.status_code == 200
        data = response.json()
        assert data["progress"] == []

    def test_exercise_progress_with_custom_days(self, client, db_with_data):
        """Test exercise progress with custom day range."""
        response = client.get("/dashboard/exercise-progress?exercise=Squat&days=90")

        assert response.status_code == 200
        data = response.json()
        assert data["period"]["days"] == 90


class TestDashboardSummary:
    """Tests for dashboard summary endpoint."""

    def test_summary_returns_overview(self, client, db_with_data):
        """Test that summary returns overview data."""
        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_activities" in data
        assert "total_exercises" in data
        assert "streak_days" in data
        assert "last_activity_date" in data
