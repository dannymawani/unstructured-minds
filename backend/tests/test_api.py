"""Tests for FastAPI application."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

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

        # Create directories
        mock_settings.vault_path.mkdir(parents=True, exist_ok=True)
        mock_settings.data_path.mkdir(parents=True, exist_ok=True)

        with patch("src.main.settings", mock_settings), \
             patch("src.api.routes.settings", mock_settings):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app
    with TestClient(app) as client:
        yield client


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client: TestClient) -> None:
        """Test health response contains ok status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_version(self, client: TestClient) -> None:
        """Test health response contains version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_health_returns_timestamp(self, client: TestClient) -> None:
        """Test health response contains timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data

    def test_health_returns_claude_status(self, client: TestClient) -> None:
        """Test health response includes claude_enabled."""
        response = client.get("/health")
        data = response.json()
        assert "claude_enabled" in data
        assert isinstance(data["claude_enabled"], bool)


class TestStatusEndpoint:
    """Tests for status endpoint."""

    def test_status_returns_200(self, client: TestClient) -> None:
        """Test status endpoint returns 200."""
        response = client.get("/status")
        assert response.status_code == 200

    def test_status_returns_database_status(self, client: TestClient) -> None:
        """Test status includes database status."""
        response = client.get("/status")
        data = response.json()
        assert "database" in data
        assert data["database"] == "connected"

    def test_status_returns_storage_status(self, client: TestClient) -> None:
        """Test status includes storage status."""
        response = client.get("/status")
        data = response.json()
        assert "storage" in data
        assert data["storage"] == "connected"

    def test_status_returns_paths(self, client: TestClient) -> None:
        """Test status includes configured paths."""
        response = client.get("/status")
        data = response.json()
        assert "vault_path" in data
        assert "data_path" in data


class TestConfig:
    """Tests for configuration."""

    def test_config_loads(self) -> None:
        """Test settings can be imported and accessed."""
        from src.config import settings
        assert settings.vault_path is not None
        assert settings.data_path is not None

    def test_config_has_server_settings(self) -> None:
        """Test settings include server configuration."""
        from src.config import settings
        assert hasattr(settings, "host")
        assert hasattr(settings, "port")

    def test_claude_enabled_property(self) -> None:
        """Test claude_enabled property works."""
        from src.config import settings
        # Without API key, should be False
        assert isinstance(settings.claude_enabled, bool)
