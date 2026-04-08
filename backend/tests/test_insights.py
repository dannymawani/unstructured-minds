"""Tests for insights API endpoints."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

    # Insert activities for patterns
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

    # Insert daily metrics for trends
    for i in range(14):
        day = today - timedelta(days=i)
        # Make sleep trend up for last week
        sleep = 7.0 if i >= 7 else 7.5 + (7 - i) * 0.1
        db.execute(
            """
            INSERT INTO daily_metrics (date, sleep_hours, energy, mood, stress)
            VALUES (?, ?, ?, ?, ?)
            """,
            [str(day), sleep, 6 + (i % 4), 7 + (i % 3), 4 - (i % 3)],
        )

    # Insert incomplete tasks
    db.execute(
        """
        INSERT INTO tasks (id, date, description, status, category)
        VALUES (?, ?, ?, ?, ?)
        """,
        ["task_1", str(today - timedelta(days=1)), "Review code", "backlog", "work"],
    )
    db.execute(
        """
        INSERT INTO tasks (id, date, description, status, category)
        VALUES (?, ?, ?, ?, ?)
        """,
        ["task_2", str(today - timedelta(days=2)), "Write tests", "in_progress", "work"],
    )

    return db


class TestDailyInsights:
    """Tests for daily insights endpoint."""

    def test_daily_insights_returns_data(self, client, db_with_data):
        """Test that daily insights returns insight list."""
        response = client.get("/insights/daily")

        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert "generated_at" in data
        assert isinstance(data["insights"], list)

    def test_daily_insights_fallback_without_claude(self, client, db_with_data):
        """Test that insights work without Claude configured."""
        response = client.get("/insights/daily")

        assert response.status_code == 200
        data = response.json()
        # Should return fallback insights
        assert len(data["insights"]) > 0

    def test_daily_insights_has_required_fields(self, client, db_with_data):
        """Test that each insight has required fields."""
        response = client.get("/insights/daily")

        data = response.json()
        if data["insights"]:
            insight = data["insights"][0]
            assert "id" in insight
            assert "type" in insight
            assert "title" in insight
            assert "message" in insight
            assert "priority" in insight

    def test_daily_insights_includes_incomplete_tasks(self, client, db_with_data):
        """Test that incomplete tasks generate an insight."""
        response = client.get("/insights/daily")

        data = response.json()
        insights = data["insights"]

        # Should have a follow_up insight about incomplete tasks
        task_insights = [i for i in insights if i["type"] == "follow_up"]
        assert len(task_insights) > 0

    def test_daily_insights_empty_db(self, client):
        """Test insights with empty database."""
        response = client.get("/insights/daily")

        assert response.status_code == 200
        data = response.json()
        # Should still return successfully, possibly with empty insights
        assert "insights" in data

    def test_daily_insights_insight_types_valid(self, client, db_with_data):
        """Test that insight types are valid."""
        response = client.get("/insights/daily")

        data = response.json()
        valid_types = {"pattern", "trend", "reminder", "follow_up"}

        for insight in data["insights"]:
            assert insight["type"] in valid_types

    def test_daily_insights_priority_range(self, client, db_with_data):
        """Test that priorities are within valid range."""
        response = client.get("/insights/daily")

        data = response.json()

        for insight in data["insights"]:
            assert 1 <= insight["priority"] <= 3


class TestWeeklySummary:
    """Tests for weekly summary endpoint."""

    def test_weekly_summary_returns_data(self, client, db_with_data):
        """Test that weekly summary returns expected structure."""
        response = client.get("/insights/weekly")

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "highlights" in data
        assert "period_start" in data
        assert "period_end" in data

    def test_weekly_summary_fallback_without_claude(self, client, db_with_data):
        """Test that weekly summary works without Claude."""
        response = client.get("/insights/weekly")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["summary"], str)
        assert isinstance(data["highlights"], list)

    def test_weekly_summary_has_period_dates(self, client, db_with_data):
        """Test that period dates are valid."""
        response = client.get("/insights/weekly")

        data = response.json()

        # Period should be 7 days
        from datetime import datetime
        start = datetime.strptime(data["period_start"], "%Y-%m-%d")
        end = datetime.strptime(data["period_end"], "%Y-%m-%d")
        assert (end - start).days == 6

    def test_weekly_summary_empty_db(self, client):
        """Test weekly summary with empty database."""
        response = client.get("/insights/weekly")

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestDismissInsight:
    """Tests for dismiss insight endpoint."""

    def test_dismiss_insight_success(self, client):
        """Test that dismissing insight returns success."""
        response = client.post("/insights/dismiss/insight_0")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"
        assert data["insight_id"] == "insight_0"

    def test_dismiss_insight_any_id(self, client):
        """Test that any insight ID can be dismissed."""
        response = client.post("/insights/dismiss/any_random_id_123")

        assert response.status_code == 200
        data = response.json()
        assert data["insight_id"] == "any_random_id_123"


class TestInsightsWithClaude:
    """Tests for insights with Claude configured."""

    def test_daily_insights_uses_claude(self, client, db_with_data):
        """Test that insights use Claude when configured."""
        from src.main import app

        # Mock Claude client
        mock_claude = MagicMock()
        mock_claude.is_configured = True
        mock_claude.query = AsyncMock(return_value='''[
            {"type": "pattern", "title": "Test Pattern", "message": "This is a test pattern insight.", "priority": 3}
        ]''')

        original_claude = app.state.claude
        app.state.claude = mock_claude

        try:
            response = client.get("/insights/daily")

            assert response.status_code == 200
            data = response.json()
            # When Claude is used, should have insights from Claude
            assert len(data["insights"]) > 0
        finally:
            app.state.claude = original_claude

    def test_weekly_summary_uses_claude(self, client, db_with_data):
        """Test that weekly summary uses Claude when configured."""
        from src.main import app

        # Mock Claude client
        mock_claude = MagicMock()
        mock_claude.is_configured = True
        mock_claude.query = AsyncMock(return_value='''{
            "summary": "Great week! You achieved your goals.",
            "highlights": ["5 workouts completed", "Sleep improved 10%"]
        }''')

        original_claude = app.state.claude
        app.state.claude = mock_claude

        try:
            response = client.get("/insights/weekly")

            assert response.status_code == 200
            data = response.json()
            assert "summary" in data
            assert isinstance(data["highlights"], list)
        finally:
            app.state.claude = original_claude

    def test_fallback_on_claude_error(self, client, db_with_data):
        """Test that fallback works when Claude fails."""
        from src.main import app

        # Mock Claude client that fails
        mock_claude = MagicMock()
        mock_claude.is_configured = True
        mock_claude.query = AsyncMock(side_effect=Exception("API error"))

        original_claude = app.state.claude
        app.state.claude = mock_claude

        try:
            response = client.get("/insights/daily")

            # Should still succeed with fallback
            assert response.status_code == 200
            data = response.json()
            assert "insights" in data
        finally:
            app.state.claude = original_claude
