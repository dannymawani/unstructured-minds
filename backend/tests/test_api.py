"""Tests for FastAPI application."""

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

        # Create directories
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


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client: TestClient) -> None:
        """Test health response contains healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_returns_timestamp(self, client: TestClient) -> None:
        """Test health response contains timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data


class TestLivenessEndpoint:
    """Tests for liveness endpoint."""

    def test_liveness_returns_200(self, client: TestClient) -> None:
        """Test liveness endpoint returns 200."""
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_liveness_returns_alive(self, client: TestClient) -> None:
        """Test liveness response indicates alive."""
        response = client.get("/health/live")
        data = response.json()
        assert data["alive"] is True
        assert data["status"] == "healthy"

    def test_liveness_returns_uptime(self, client: TestClient) -> None:
        """Test liveness response includes uptime."""
        response = client.get("/health/live")
        data = response.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))


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


class TestVaultListFiles:
    """Tests for vault file listing endpoint."""

    def test_list_files_empty_vault(self, client: TestClient) -> None:
        """Test listing files in empty vault."""
        response = client.get("/vault/files")
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert data["files"] == []

    def test_list_files_with_files(self, client: TestClient, test_settings) -> None:
        """Test listing files after creating some."""
        # Create test files
        vault_path = test_settings.vault_path
        (vault_path / "test.md").write_text("# Test")
        (vault_path / "notes").mkdir()
        (vault_path / "notes" / "note1.md").write_text("# Note 1")

        response = client.get("/vault/files")
        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) > 0

    def test_list_files_with_prefix(self, client: TestClient, test_settings) -> None:
        """Test listing files with prefix filter."""
        vault_path = test_settings.vault_path
        (vault_path / "daily").mkdir()
        (vault_path / "daily" / "2026-01-31.md").write_text("# Daily")
        (vault_path / "other.md").write_text("# Other")

        response = client.get("/vault/files?prefix=daily")
        assert response.status_code == 200
        data = response.json()
        # Should have files from daily folder
        paths = [f["path"] for f in data["files"]]
        assert any("daily" in p for p in paths)


class TestVaultReadFile:
    """Tests for vault file read endpoint."""

    def test_read_file_success(self, client: TestClient, test_settings) -> None:
        """Test reading a file."""
        vault_path = test_settings.vault_path
        (vault_path / "test.md").write_text("# Hello World")

        response = client.get("/vault/file?path=test.md")
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "test.md"
        assert data["content"] == "# Hello World"

    def test_read_file_not_found(self, client: TestClient) -> None:
        """Test reading a nonexistent file."""
        response = client.get("/vault/file?path=nonexistent.md")
        assert response.status_code == 404

    def test_read_file_path_required(self, client: TestClient) -> None:
        """Test that path parameter is required."""
        response = client.get("/vault/file")
        assert response.status_code == 422  # Validation error


class TestVaultWriteFile:
    """Tests for vault file write endpoint."""

    def test_write_file_success(self, client: TestClient, test_settings) -> None:
        """Test writing a file."""
        response = client.post(
            "/vault/file",
            json={"path": "new-file.md", "content": "# New Content"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "new-file.md"
        assert data["success"] is True

        # Verify file was written
        vault_path = test_settings.vault_path
        assert (vault_path / "new-file.md").exists()
        assert (vault_path / "new-file.md").read_text() == "# New Content"

    def test_write_file_creates_directories(self, client: TestClient, test_settings) -> None:
        """Test writing a file creates parent directories."""
        response = client.post(
            "/vault/file",
            json={"path": "nested/dir/file.md", "content": "# Nested"},
        )
        assert response.status_code == 200

        vault_path = test_settings.vault_path
        assert (vault_path / "nested" / "dir" / "file.md").exists()

    def test_write_file_overwrites(self, client: TestClient, test_settings) -> None:
        """Test writing overwrites existing file."""
        vault_path = test_settings.vault_path
        (vault_path / "existing.md").write_text("# Original")

        response = client.post(
            "/vault/file",
            json={"path": "existing.md", "content": "# Updated"},
        )
        assert response.status_code == 200
        assert (vault_path / "existing.md").read_text() == "# Updated"


class TestVaultDeleteFile:
    """Tests for vault file delete endpoint."""

    def test_delete_file_success(self, client: TestClient, test_settings) -> None:
        """Test deleting a file."""
        vault_path = test_settings.vault_path
        (vault_path / "delete-me.md").write_text("# Delete me")

        response = client.delete("/vault/file?path=delete-me.md")
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "delete-me.md"
        assert data["success"] is True

        # Verify file was deleted
        assert not (vault_path / "delete-me.md").exists()

    def test_delete_file_not_found(self, client: TestClient) -> None:
        """Test deleting a nonexistent file."""
        response = client.delete("/vault/file?path=nonexistent.md")
        assert response.status_code == 404

    def test_delete_file_path_required(self, client: TestClient) -> None:
        """Test that path parameter is required."""
        response = client.delete("/vault/file")
        assert response.status_code == 422


class TestVaultRenameFile:
    """Tests for vault file rename endpoint."""

    def test_rename_file_success(self, client: TestClient, test_settings) -> None:
        """Test renaming a file."""
        vault_path = test_settings.vault_path
        (vault_path / "old-name.md").write_text("# Content")

        response = client.patch(
            "/vault/file",
            json={"old_path": "old-name.md", "new_path": "new-name.md"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["old_path"] == "old-name.md"
        assert data["new_path"] == "new-name.md"
        assert data["success"] is True

        # Verify file was renamed
        assert not (vault_path / "old-name.md").exists()
        assert (vault_path / "new-name.md").exists()
        assert (vault_path / "new-name.md").read_text() == "# Content"

    def test_rename_file_not_found(self, client: TestClient) -> None:
        """Test renaming a nonexistent file."""
        response = client.patch(
            "/vault/file",
            json={"old_path": "nonexistent.md", "new_path": "new.md"},
        )
        assert response.status_code == 404

    def test_rename_file_dest_exists(self, client: TestClient, test_settings) -> None:
        """Test renaming to an existing destination returns 409."""
        vault_path = test_settings.vault_path
        (vault_path / "a.md").write_text("# A")
        (vault_path / "b.md").write_text("# B")

        response = client.patch(
            "/vault/file",
            json={"old_path": "a.md", "new_path": "b.md"},
        )
        assert response.status_code == 409

    def test_rename_file_paths_required(self, client: TestClient) -> None:
        """Test that both path parameters are required."""
        response = client.patch("/vault/file", json={})
        assert response.status_code == 422
