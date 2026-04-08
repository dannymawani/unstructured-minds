"""Tests for the templates API."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.templates import (
    extract_template_description,
    router,
    substitute_variables,
)


class TestSubstituteVariables:
    """Tests for template variable substitution."""

    def test_substitute_title(self):
        """Test {{title}} substitution."""
        result = substitute_variables("# {{title}}", "My Note")
        assert result == "# My Note"

    def test_substitute_date_default(self):
        """Test {{date}} substitution with default format."""
        result = substitute_variables("Date: {{date}}", "Test")
        today = datetime.now().strftime("%Y-%m-%d")
        assert result == f"Date: {today}"

    def test_substitute_date_custom_format(self):
        """Test {{date:FORMAT}} substitution."""
        result = substitute_variables("Year: {{date:YYYY}}", "Test")
        year = datetime.now().strftime("%Y")
        assert result == f"Year: {year}"

    def test_substitute_date_month_format(self):
        """Test {{date:YYYY-MM}} substitution."""
        result = substitute_variables("Month: {{date:YYYY-MM}}", "Test")
        ym = datetime.now().strftime("%Y-%m")
        assert result == f"Month: {ym}"

    def test_substitute_time_default(self):
        """Test {{time}} substitution with default format."""
        result = substitute_variables("Time: {{time}}", "Test")
        # Just check format, not exact time
        assert result.startswith("Time: ")
        time_part = result.replace("Time: ", "")
        assert len(time_part) == 5  # HH:MM
        assert ":" in time_part

    def test_substitute_time_custom_format(self):
        """Test {{time:FORMAT}} substitution."""
        result = substitute_variables("Time: {{time:HH:mm:ss}}", "Test")
        time_part = result.replace("Time: ", "")
        assert len(time_part) == 8  # HH:MM:SS
        assert time_part.count(":") == 2

    def test_substitute_datetime(self):
        """Test {{datetime}} substitution."""
        result = substitute_variables("Created: {{datetime}}", "Test")
        assert result.startswith("Created: ")
        # ISO format includes T
        assert "T" in result

    def test_substitute_multiple_variables(self):
        """Test multiple variable substitution."""
        template = """# {{title}}
Date: {{date}}
Time: {{time}}
"""
        result = substitute_variables(template, "My Document")
        assert "# My Document" in result
        assert "Date:" in result
        assert "Time:" in result

    def test_substitute_repeated_variables(self):
        """Test repeated variables are all substituted."""
        template = "{{title}} - {{title}}"
        result = substitute_variables(template, "Note")
        assert result == "Note - Note"


class TestExtractTemplateDescription:
    """Tests for template description extraction."""

    def test_extract_from_frontmatter(self):
        """Test extraction from frontmatter description field."""
        content = """---
date: 2026-01-01
description: My template description
---

# Content
"""
        result = extract_template_description(content)
        assert result == "My template description"

    def test_extract_from_frontmatter_quoted(self):
        """Test extraction from quoted frontmatter description."""
        content = """---
description: "A quoted description"
---
"""
        result = extract_template_description(content)
        assert result == "A quoted description"

    def test_extract_from_heading(self):
        """Test extraction from first heading when no frontmatter description."""
        content = """---
date: 2026-01-01
---

# My Template Title
"""
        result = extract_template_description(content)
        assert result == "My Template Title"

    def test_extract_from_heading_no_frontmatter(self):
        """Test extraction from heading when no frontmatter."""
        content = "# Just a Heading\n\nSome content"
        result = extract_template_description(content)
        assert result == "Just a Heading"

    def test_default_when_no_description(self):
        """Test default value when no description found."""
        content = "Just some plain content"
        result = extract_template_description(content)
        assert result == "Template"


class TestTemplatesAPI:
    """Integration tests for templates API endpoints."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage backend."""
        storage = MagicMock()
        storage.list = AsyncMock(return_value=[
            "Templates/daily.md",
            "Templates/meeting.md",
            "Templates/project.md",
        ])
        storage.read = AsyncMock(return_value=b"""---
description: Daily note template
---

# {{title}}
""")
        storage.exists = AsyncMock(return_value=False)
        storage.write = AsyncMock()
        return storage

    @pytest.fixture
    def app(self, mock_storage):
        """Create test app with mock storage."""
        from fastapi import FastAPI

        app = FastAPI()
        app.state.storage = mock_storage
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_list_templates(self, client):
        """Test listing templates."""
        response = client.get("/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) == 3
        names = [t["name"] for t in data["templates"]]
        assert "daily" in names
        assert "meeting" in names
        assert "project" in names

    def test_list_templates_empty_folder(self, client, mock_storage):
        """Test listing when templates folder doesn't exist."""
        mock_storage.list = AsyncMock(side_effect=FileNotFoundError())
        response = client.get("/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["templates"] == []

    def test_get_template(self, client):
        """Test getting template content."""
        response = client.get("/templates/daily")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "daily"
        assert "{{title}}" in data["content"]

    def test_get_template_not_found(self, client, mock_storage):
        """Test getting non-existent template."""
        mock_storage.read = AsyncMock(side_effect=FileNotFoundError())
        response = client.get("/templates/nonexistent")
        assert response.status_code == 404

    def test_create_from_template(self, client, mock_storage):
        """Test creating note from template."""
        response = client.post("/notes/from-template", json={
            "template_name": "daily",
            "title": "My New Note",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["path"] == "My New Note.md"

        # Verify storage.write was called
        mock_storage.write.assert_called_once()
        call_args = mock_storage.write.call_args
        assert call_args[0][0] == "My New Note.md"
        # Check content was substituted
        content = call_args[0][1].decode("utf-8")
        assert "My New Note" in content

    def test_create_from_template_with_folder(self, client, mock_storage):
        """Test creating note from template in specific folder."""
        response = client.post("/notes/from-template", json={
            "template_name": "daily",
            "title": "My Note",
            "folder": "Projects/2026",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "Projects/2026/My Note.md"

    def test_create_from_template_already_exists(self, client, mock_storage):
        """Test creating note when file already exists."""
        mock_storage.exists = AsyncMock(return_value=True)
        response = client.post("/notes/from-template", json={
            "template_name": "daily",
            "title": "Existing Note",
        })
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_from_template_not_found(self, client, mock_storage):
        """Test creating from non-existent template."""
        mock_storage.read = AsyncMock(side_effect=FileNotFoundError())
        response = client.post("/notes/from-template", json={
            "template_name": "nonexistent",
            "title": "My Note",
        })
        assert response.status_code == 404

    def test_create_from_template_sanitizes_title(self, client, mock_storage):
        """Test that invalid characters in title are sanitized."""
        response = client.post("/notes/from-template", json={
            "template_name": "daily",
            "title": "My/Note:With<Invalid>Chars",
        })
        assert response.status_code == 200
        data = response.json()
        # Invalid chars should be replaced with dashes
        assert "/" not in data["path"].replace("Templates/", "")
        assert ":" not in data["path"]
        assert "<" not in data["path"]
        assert ">" not in data["path"]
