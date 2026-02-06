"""Tests for personal tasks API endpoints."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

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

        with patch("src.main.settings", mock_settings), \
             patch("src.api.routes.settings", mock_settings):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seeded_client(client):
    """Client with some test tasks in the database."""
    from src.main import app

    db = app.state.db
    db.execute(
        """INSERT INTO tasks (id, date, description, status, category, priority, source_file)
           VALUES
           ('t1', '2026-02-01', 'Write tests', 'pending', 'work', 1, 'Daily-Notes/2026-02/2026-02-01.md'),
           ('t2', '2026-02-01', 'Buy groceries', 'completed', 'personal', 2, NULL),
           ('t3', '2026-02-05', 'Review PR', 'pending', 'work', 1, 'Daily-Notes/2026-02/2026-02-05.md')
        """
    )
    return client


class TestListTasks:
    def test_list_empty(self, client):
        response = client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    def test_list_returns_tasks(self, seeded_client):
        response = seeded_client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["tasks"]) == 3

    def test_filter_by_status(self, seeded_client):
        response = seeded_client.get("/tasks?status=pending")
        data = response.json()
        assert data["total"] == 2
        assert all(t["status"] == "pending" for t in data["tasks"])

    def test_filter_by_category(self, seeded_client):
        response = seeded_client.get("/tasks?category=work")
        data = response.json()
        assert data["total"] == 2

    def test_filter_by_date_range(self, seeded_client):
        response = seeded_client.get("/tasks?date_from=2026-02-03&date_to=2026-02-06")
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["id"] == "t3"

    def test_pagination(self, seeded_client):
        response = seeded_client.get("/tasks?limit=1&offset=0")
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["total"] == 3


class TestGetTask:
    def test_get_existing(self, seeded_client):
        response = seeded_client.get("/tasks/t1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "t1"
        assert data["description"] == "Write tests"

    def test_get_not_found(self, seeded_client):
        response = seeded_client.get("/tasks/nonexistent")
        assert response.status_code == 404


class TestUpdateTask:
    def test_update_status(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={"status": "completed"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_update_status_clears_completed_at(self, seeded_client):
        seeded_client.patch("/tasks/t1", json={"status": "completed"})
        response = seeded_client.patch("/tasks/t1", json={"status": "pending"})
        data = response.json()
        assert data["status"] == "pending"
        assert data["completed_at"] is None

    def test_update_priority(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={"priority": 3})
        assert response.status_code == 200
        assert response.json()["priority"] == 3

    def test_update_not_found(self, seeded_client):
        response = seeded_client.patch("/tasks/nonexistent", json={"status": "completed"})
        assert response.status_code == 404

    def test_update_no_fields(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={})
        assert response.status_code == 400


class TestCreateTask:
    def test_create_task(self, client):
        response = client.post("/tasks", json={"description": "New task"})
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "New task"
        assert data["status"] == "pending"
        assert data["source_file"] is not None

    def test_create_task_with_category(self, client):
        response = client.post(
            "/tasks",
            json={"description": "Gym session", "category": "training", "priority": 1},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "training"
        assert data["priority"] == 1

    def test_create_empty_description(self, client):
        response = client.post("/tasks", json={"description": ""})
        assert response.status_code == 422
