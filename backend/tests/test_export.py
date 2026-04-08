"""Tests for Export and Import API endpoints."""

import io
import zipfile
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
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.claude_enabled = True
        mock_settings.database_url = None
        mock_settings.is_cloud_mode = False
        mock_settings.cors_origins = "http://localhost:3000"

        mock_settings.vault_path.mkdir(parents=True, exist_ok=True)
        mock_settings.data_path.mkdir(parents=True, exist_ok=True)

        with (
            patch("src.main.settings", mock_settings),
            patch("src.api.settings.settings", mock_settings),
            patch("src.api.export.settings", mock_settings),
        ):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_vault(test_settings):
    """Create test files in the vault."""
    vault_path = test_settings.vault_path

    # Create some test files
    (vault_path / "note1.md").write_text("# Test Note 1\nSome content here.")
    (vault_path / "note2.md").write_text("# Test Note 2\nMore content.")

    # Create a subdirectory with files
    daily_notes = vault_path / "Daily-Notes"
    daily_notes.mkdir()
    (daily_notes / "2024-01-15.md").write_text("# Daily Note\n- Task 1\n- Task 2")

    return vault_path


class TestExportVault:
    """Tests for vault export endpoint."""

    def test_export_vault_success(self, client, temp_vault):
        """Test successful vault export."""
        response = client.get("/export/vault")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Verify ZIP contents
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            names = zf.namelist()
            assert "note1.md" in names
            assert "note2.md" in names
            assert "Daily-Notes/2024-01-15.md" in names

    def test_export_vault_empty(self, client):
        """Test export with empty vault returns empty ZIP."""
        response = client.get("/export/vault")

        assert response.status_code == 200
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            assert zf.namelist() == []


class TestExportData:
    """Tests for data export endpoint."""

    def test_export_data_csv(self, client):
        """Test exporting data as CSV."""
        response = client.get("/export/data?format=csv")

        # May return 404 if no data tables, or 200 with ZIP
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            assert response.headers["content-type"] == "application/zip"
            zip_buffer = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                names = zf.namelist()
                # Should contain CSV files
                assert all(name.endswith(".csv") for name in names)

    def test_export_data_json(self, client):
        """Test exporting data as JSON."""
        response = client.get("/export/data?format=json")

        # May return 404 if no data tables, or 200 with ZIP
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            assert response.headers["content-type"] == "application/zip"
            zip_buffer = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                names = zf.namelist()
                # Should contain JSON files
                assert all(name.endswith(".json") for name in names)

    def test_list_export_tables(self, client):
        """Test listing available tables for export."""
        response = client.get("/export/data/tables")

        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "format" in data
        assert isinstance(data["tables"], list)


class TestImportVault:
    """Tests for vault import endpoint."""

    def test_import_vault_success(self, client, test_settings):
        """Test successful vault import."""
        vault_path = test_settings.vault_path

        # Create a ZIP file to import
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("imported_note.md", "# Imported Note\nContent here.")
            zf.writestr("subdir/another.md", "# Another Note\nMore content.")

        zip_buffer.seek(0)

        response = client.post(
            "/import/vault",
            files={"file": ("backup.zip", zip_buffer, "application/zip")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["files_imported"] == 2

        # Verify files were written to vault
        assert (vault_path / "imported_note.md").exists()
        assert (vault_path / "subdir" / "another.md").exists()

    def test_import_vault_invalid_file(self, client):
        """Test import with non-ZIP file."""
        response = client.post(
            "/import/vault",
            files={"file": ("backup.txt", b"not a zip file", "text/plain")},
        )

        assert response.status_code == 400

    def test_import_vault_bad_zip(self, client):
        """Test import with corrupted ZIP."""
        response = client.post(
            "/import/vault",
            files={"file": ("backup.zip", b"not actually a zip", "application/zip")},
        )

        assert response.status_code == 400

    def test_import_vault_path_traversal(self, client, test_settings):
        """Test that path traversal attacks are blocked."""
        # Create a ZIP with path traversal attempt
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("../../../etc/passwd", "malicious content")

        zip_buffer.seek(0)

        response = client.post(
            "/import/vault",
            files={"file": ("backup.zip", zip_buffer, "application/zip")},
        )

        assert response.status_code == 400
        assert "Invalid path" in response.json().get("detail", "")
