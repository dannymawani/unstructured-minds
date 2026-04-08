"""Tests for schema management API."""

import json
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

        mock_settings.vault_path.mkdir(parents=True, exist_ok=True)
        mock_settings.data_path.mkdir(parents=True, exist_ok=True)
        (mock_settings.data_path / "schemas").mkdir(parents=True, exist_ok=True)

        with (
            patch("src.main.settings", mock_settings),
            patch("src.api.settings.settings", mock_settings),
        ):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app

    with TestClient(app) as client:
        yield client


class TestListSchemas:
    """Tests for GET /schemas."""

    def test_list_includes_builtin_schemas(self, client):
        """Should return built-in schemas."""
        response = client.get("/schemas")
        assert response.status_code == 200

        data = response.json()
        schemas = data["schemas"]

        # Check built-in schemas are present
        names = [s["name"] for s in schemas]
        assert "exercise" in names
        assert "daily_metrics" in names
        assert "tasks" in names
        assert "food_log" in names
        assert "combined" in names

        # Check is_builtin flag
        for schema in schemas:
            if schema["name"] in [
                "exercise",
                "daily_metrics",
                "tasks",
                "food_log",
                "combined",
            ]:
                assert schema["is_builtin"] is True

    def test_list_includes_custom_schemas(self, client, test_settings):
        """Should return custom schemas from disk."""
        # Create a custom schema file
        custom_schema = {
            "name": "test_schema",
            "description": "A test schema",
            "fields": [{"name": "title", "type": "string", "required": True}],
        }
        schemas_dir = test_settings.data_path / "schemas"
        schema_path = schemas_dir / "test_schema.json"
        schema_path.write_text(json.dumps(custom_schema))

        response = client.get("/schemas")
        assert response.status_code == 200

        data = response.json()
        schemas = data["schemas"]
        names = [s["name"] for s in schemas]

        assert "test_schema" in names

        # Find the custom schema and verify it's not built-in
        custom = next(s for s in schemas if s["name"] == "test_schema")
        assert custom["is_builtin"] is False
        assert custom["field_count"] == 1


class TestGetSchema:
    """Tests for GET /schemas/{name}."""

    def test_get_builtin_schema(self, client):
        """Should return details of a built-in schema."""
        response = client.get("/schemas/exercise")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "exercise"
        assert data["is_builtin"] is True
        assert "fields" in data
        assert "json_schema" in data

    def test_get_custom_schema(self, client, test_settings):
        """Should return details of a custom schema."""
        custom_schema = {
            "name": "book_notes",
            "description": "Extract book reading notes",
            "fields": [
                {"name": "title", "type": "string", "required": True},
                {"name": "author", "type": "string", "required": False},
                {"name": "rating", "type": "integer", "min": 1, "max": 5},
            ],
            "extraction_hints": "Look for book titles in headers",
        }
        schemas_dir = test_settings.data_path / "schemas"
        schema_path = schemas_dir / "book_notes.json"
        schema_path.write_text(json.dumps(custom_schema))

        response = client.get("/schemas/book_notes")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "book_notes"
        assert data["description"] == "Extract book reading notes"
        assert data["is_builtin"] is False
        assert len(data["fields"]) == 3
        assert data["extraction_hints"] == "Look for book titles in headers"

    def test_get_nonexistent_schema(self, client):
        """Should return 404 for unknown schema."""
        response = client.get("/schemas/nonexistent")
        assert response.status_code == 404


class TestCreateSchema:
    """Tests for POST /schemas."""

    def test_create_valid_schema(self, client, test_settings):
        """Should create a new custom schema."""
        schema = {
            "name": "new_schema",
            "description": "A new test schema",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }

        response = client.post("/schemas", json=schema)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["name"] == "new_schema"

        # Verify file was created
        schemas_dir = test_settings.data_path / "schemas"
        schema_file = schemas_dir / "new_schema.json"
        assert schema_file.exists()

    def test_create_schema_invalid_name(self, client):
        """Should reject schema with invalid name."""
        schema = {
            "name": "Invalid-Name",  # Contains dash and uppercase
            "description": "A test schema",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }

        response = client.post("/schemas", json=schema)
        assert response.status_code == 422  # Validation error

    def test_create_schema_builtin_name(self, client):
        """Should reject schema with built-in name."""
        schema = {
            "name": "exercise",  # Built-in name
            "description": "A test schema",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }

        response = client.post("/schemas", json=schema)
        assert response.status_code == 422  # Validation error

    def test_create_duplicate_schema(self, client, test_settings):
        """Should reject duplicate schema name."""
        schema = {
            "name": "duplicate_test",
            "description": "A test schema",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }

        # Create first
        response = client.post("/schemas", json=schema)
        assert response.status_code == 200

        # Try to create again
        response = client.post("/schemas", json=schema)
        assert response.status_code == 400


class TestUpdateSchema:
    """Tests for PUT /schemas/{name}."""

    def test_update_custom_schema(self, client, test_settings):
        """Should update an existing custom schema."""
        # Create initial schema
        schema = {
            "name": "update_test",
            "description": "Initial description",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }
        schemas_dir = test_settings.data_path / "schemas"
        schema_path = schemas_dir / "update_test.json"
        schema_path.write_text(json.dumps(schema))

        # Update it
        updated = {
            "name": "update_test",
            "description": "Updated description",
            "fields": [
                {"name": "field1", "type": "string", "required": True},
                {"name": "field2", "type": "integer", "required": False},
            ],
        }

        response = client.put("/schemas/update_test", json=updated)
        assert response.status_code == 200

        # Verify update
        response = client.get("/schemas/update_test")
        data = response.json()
        assert data["description"] == "Updated description"
        assert len(data["fields"]) == 2

    def test_update_builtin_schema(self, client):
        """Should reject updating built-in schema."""
        schema = {
            "name": "exercise",
            "description": "Modified",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }

        response = client.put("/schemas/exercise", json=schema)
        # Pydantic validator rejects built-in names with 422, endpoint logic returns 400
        assert response.status_code in (400, 422)

    def test_update_nonexistent_schema(self, client):
        """Should return 404 for unknown schema."""
        schema = {
            "name": "nonexistent",
            "description": "Test",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }

        response = client.put("/schemas/nonexistent", json=schema)
        assert response.status_code == 404


class TestDeleteSchema:
    """Tests for DELETE /schemas/{name}."""

    def test_delete_custom_schema(self, client, test_settings):
        """Should delete a custom schema."""
        # Create schema first
        schema = {
            "name": "delete_test",
            "description": "To be deleted",
            "fields": [{"name": "field1", "type": "string", "required": True}],
        }
        schemas_dir = test_settings.data_path / "schemas"
        schema_path = schemas_dir / "delete_test.json"
        schema_path.write_text(json.dumps(schema))

        response = client.delete("/schemas/delete_test")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deletion
        assert not schema_path.exists()

    def test_delete_builtin_schema(self, client):
        """Should reject deleting built-in schema."""
        response = client.delete("/schemas/exercise")
        assert response.status_code == 400

    def test_delete_nonexistent_schema(self, client):
        """Should return 404 for unknown schema."""
        response = client.delete("/schemas/nonexistent")
        assert response.status_code == 404


class TestGetJsonSchema:
    """Tests for GET /schemas/{name}/json-schema."""

    def test_get_builtin_json_schema(self, client):
        """Should return JSON Schema format for built-in schema."""
        response = client.get("/schemas/exercise/json-schema")
        assert response.status_code == 200

        data = response.json()
        assert data["type"] == "object"
        assert "properties" in data

    def test_get_custom_json_schema(self, client, test_settings):
        """Should convert custom schema to JSON Schema format."""
        custom_schema = {
            "name": "json_test",
            "description": "Test schema",
            "fields": [
                {"name": "title", "type": "string", "required": True},
                {"name": "count", "type": "integer", "min": 0, "max": 100},
            ],
        }
        schemas_dir = test_settings.data_path / "schemas"
        schema_path = schemas_dir / "json_test.json"
        schema_path.write_text(json.dumps(custom_schema))

        response = client.get("/schemas/json_test/json-schema")
        assert response.status_code == 200

        data = response.json()
        assert data["type"] == "object"
        assert "title" in data["properties"]
        assert "count" in data["properties"]
        assert data["properties"]["count"]["minimum"] == 0
        assert data["properties"]["count"]["maximum"] == 100
        assert "title" in data.get("required", [])
