"""Tests for Export and Import API endpoints."""

import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.config import settings


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault with test files."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

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

    def test_export_vault_success(self, client, temp_vault, monkeypatch):
        """Test successful vault export."""
        # Temporarily override vault path
        monkeypatch.setattr(settings, "vault_path", temp_vault)

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

    def test_export_vault_not_found(self, client, tmp_path, monkeypatch):
        """Test export when vault doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setattr(settings, "vault_path", nonexistent)

        response = client.get("/export/vault")

        assert response.status_code == 404


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

    def test_import_vault_success(self, client, tmp_path, monkeypatch):
        """Test successful vault import."""
        # Create a temporary vault path
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        monkeypatch.setattr(settings, "vault_path", vault_path)

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

        # Verify files were extracted
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

    def test_import_vault_path_traversal(self, client, tmp_path, monkeypatch):
        """Test that path traversal attacks are blocked."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        monkeypatch.setattr(settings, "vault_path", vault_path)

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
