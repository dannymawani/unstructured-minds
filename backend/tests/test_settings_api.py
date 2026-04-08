"""Tests for settings API endpoints."""

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
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.claude_enabled = True
        mock_settings.database_url = None
        mock_settings.is_cloud_mode = False

        mock_settings.vault_path.mkdir(parents=True, exist_ok=True)
        mock_settings.data_path.mkdir(parents=True, exist_ok=True)

        with patch("src.main.settings", mock_settings), \
             patch("src.api.settings.settings", mock_settings):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app
    with TestClient(app) as client:
        yield client


class TestGetSettings:
    """Tests for GET /settings endpoint."""

    def test_returns_settings(self, client):
        """Test that settings are returned."""
        response = client.get("/settings")

        assert response.status_code == 200
        data = response.json()
        assert "vault_path" in data
        assert "data_path" in data
        assert "claude_enabled" in data
        assert "api_key_set" in data

    def test_api_key_not_exposed(self, client):
        """Test that API key value is not exposed."""
        response = client.get("/settings")

        data = response.json()
        # Should indicate if key is set, but not expose the value
        assert "api_key_set" in data
        assert "anthropic_api_key" not in data


class TestTheme:
    """Tests for theme endpoints."""

    def test_get_theme(self, client):
        """Test getting current theme."""
        response = client.get("/settings/theme")

        assert response.status_code == 200
        data = response.json()
        assert "theme" in data
        assert "available_themes" in data
        assert "dark" in data["available_themes"]
        assert "light" in data["available_themes"]

    def test_set_theme_dark(self, client):
        """Test setting dark theme."""
        response = client.post("/settings/theme?theme=dark")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"

    def test_set_theme_light(self, client):
        """Test setting light theme."""
        response = client.post("/settings/theme?theme=light")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"

    def test_invalid_theme_ignored(self, client):
        """Test that invalid theme is ignored."""
        # First set to dark
        client.post("/settings/theme?theme=dark")

        # Try to set invalid
        response = client.post("/settings/theme?theme=invalid")

        assert response.status_code == 200
        data = response.json()
        # Should remain unchanged
        assert data["theme"] in ["dark", "light"]


class TestSystemInfo:
    """Tests for system info endpoint."""

    def test_get_system_info(self, client):
        """Test getting system information."""
        response = client.get("/settings/system")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "python_version" in data
        assert "database_tables" in data
        assert "storage_type" in data

    def test_system_info_contains_tables(self, client):
        """Test that system info includes database tables."""
        response = client.get("/settings/system")

        data = response.json()
        tables = data["database_tables"]
        # Should have the core tables
        assert "activities" in tables
        assert "exercise_log" in tables
        assert "daily_metrics" in tables
