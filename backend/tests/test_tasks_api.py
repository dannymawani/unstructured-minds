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
def seeded_client(client):
    """Client with some test tasks in the database."""
    from src.main import app

    db = app.state.db
    db.execute(
        """INSERT INTO tasks (id, date, description, status, category, priority, source_file)
           VALUES
           ('t1', '2026-02-01', 'Write tests', 'backlog', 'work', 1, 'Daily-Notes/2026-02/2026-02-01.md'),
           ('t2', '2026-02-01', 'Buy groceries', 'done', 'personal', 2, NULL),
           ('t3', '2026-02-05', 'Review PR', 'backlog', 'work', 1, 'Daily-Notes/2026-02/2026-02-05.md')
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
        response = seeded_client.get("/tasks?status=backlog")
        data = response.json()
        assert data["total"] == 2
        assert all(t["status"] == "backlog" for t in data["tasks"])

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

    def test_hide_old_done_tasks(self, client):
        """Done/cancelled tasks older than 7 days are hidden by default."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status, completed_at, category)
               VALUES
               ('old1', '2026-01-01', 'Old done task', 'done', '2026-01-01T12:00:00', 'work'),
               ('old2', '2026-01-01', 'Old cancelled task', 'cancelled', '2026-01-01T12:00:00', 'work'),
               ('new1', '2026-02-07', 'Recent done task', 'done', '2026-02-07T12:00:00', 'work'),
               ('active1', '2026-02-07', 'Active task', 'backlog', NULL, 'work')
            """
        )

        # Default: hide_old=true — old done/cancelled hidden
        response = client.get("/tasks")
        data = response.json()
        ids = [t["id"] for t in data["tasks"]]
        assert "old1" not in ids
        assert "old2" not in ids
        assert "new1" in ids
        assert "active1" in ids

        # Explicit hide_old=false — all visible
        response = client.get("/tasks?hide_old=false")
        data = response.json()
        assert data["total"] == 4


class TestGetTask:
    def test_get_existing(self, seeded_client):
        response = seeded_client.get("/tasks/t1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "t1"
        assert data["description"] == "Write tests"

    def test_get_includes_notes_field(self, seeded_client):
        response = seeded_client.get("/tasks/t1")
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        assert data["notes"] is None

    def test_get_not_found(self, seeded_client):
        response = seeded_client.get("/tasks/nonexistent")
        assert response.status_code == 404


class TestUpdateTask:
    def test_update_status(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={"status": "done"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["completed_at"] is not None

    def test_update_status_clears_completed_at(self, seeded_client):
        seeded_client.patch("/tasks/t1", json={"status": "done"})
        response = seeded_client.patch("/tasks/t1", json={"status": "backlog"})
        data = response.json()
        assert data["status"] == "backlog"
        assert data["completed_at"] is None

    def test_cancelled_sets_completed_at(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={"status": "cancelled"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["completed_at"] is not None

    def test_update_priority(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={"priority": 3})
        assert response.status_code == 200
        assert response.json()["priority"] == 3

    def test_update_not_found(self, seeded_client):
        response = seeded_client.patch("/tasks/nonexistent", json={"status": "done"})
        assert response.status_code == 404

    def test_update_notes(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={"notes": "Added some notes"})
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Added some notes"

    def test_update_notes_clear(self, seeded_client):
        seeded_client.patch("/tasks/t1", json={"notes": "Some notes"})
        response = seeded_client.patch("/tasks/t1", json={"notes": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == ""

    def test_update_no_fields(self, seeded_client):
        response = seeded_client.patch("/tasks/t1", json={})
        assert response.status_code == 400


class TestCreateTask:
    def test_create_task(self, client):
        response = client.post("/tasks", json={"description": "New task"})
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "New task"
        assert data["status"] == "backlog"
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

    def test_create_task_with_notes(self, client):
        response = client.post(
            "/tasks",
            json={"description": "Task with notes", "notes": "Some detailed notes here"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["notes"] == "Some detailed notes here"

    def test_create_empty_description(self, client):
        response = client.post("/tasks", json={"description": ""})
        assert response.status_code == 422


class TestRolloverTasks:
    """Tests for GET /tasks/rollover and POST /tasks/rollover endpoints."""

    def test_rollover_empty_state(self, client):
        """No tasks returns empty list."""
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    def test_rollover_excludes_done_tasks(self, client):
        """Done tasks are not included in rollover."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status)
               VALUES
               ('r1', '2026-02-05', 'Done task', 'done'),
               ('r2', '2026-02-05', 'Active task', 'backlog')
            """
        )
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["id"] == "r2"

    def test_rollover_includes_active_within_14_days(self, client):
        """Backlog and in_progress tasks within 14 days are included."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status)
               VALUES
               ('r1', '2026-02-05', 'Backlog task', 'backlog'),
               ('r2', '2026-02-08', 'In progress task', 'in_progress')
            """
        )
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        data = response.json()
        assert data["total"] == 2
        ids = [t["id"] for t in data["tasks"]]
        assert "r1" in ids
        assert "r2" in ids

    def test_rollover_excludes_old_tasks(self, client):
        """Tasks older than 14 days are excluded."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status)
               VALUES
               ('old1', '2026-01-15', 'Old task', 'backlog'),
               ('new1', '2026-02-05', 'Recent task', 'backlog')
            """
        )
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["id"] == "new1"

    def test_rollover_excludes_target_date_tasks(self, client):
        """Tasks from the target date itself are excluded (date < target)."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status)
               VALUES
               ('same1', '2026-02-10', 'Same day task', 'backlog'),
               ('prev1', '2026-02-09', 'Previous day task', 'backlog')
            """
        )
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        data = response.json()
        assert data["total"] == 1
        assert data["tasks"][0]["id"] == "prev1"

    def test_rollover_deadline_status_computation(self, client):
        """Deadline status is correctly computed relative to target date."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status, deadline)
               VALUES
               ('d1', '2026-02-05', 'Overdue task', 'backlog', '2026-02-08'),
               ('d2', '2026-02-05', 'Due today task', 'backlog', '2026-02-10'),
               ('d3', '2026-02-05', 'Upcoming task', 'backlog', '2026-02-15'),
               ('d4', '2026-02-05', 'No deadline task', 'backlog', NULL)
            """
        )
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        data = response.json()
        tasks_by_id = {t["id"]: t for t in data["tasks"]}

        assert tasks_by_id["d1"]["deadline_status"] == "overdue"
        assert tasks_by_id["d2"]["deadline_status"] == "due_today"
        assert tasks_by_id["d3"]["deadline_status"] == "upcoming"
        assert tasks_by_id["d4"]["deadline_status"] is None

    def test_rollover_sort_order(self, client):
        """Overdue first, then due_today, then in_progress, then backlog."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status, deadline)
               VALUES
               ('s1', '2026-02-05', 'Backlog no deadline', 'backlog', NULL),
               ('s2', '2026-02-05', 'In progress', 'in_progress', NULL),
               ('s3', '2026-02-05', 'Overdue', 'backlog', '2026-02-08'),
               ('s4', '2026-02-05', 'Due today', 'backlog', '2026-02-10')
            """
        )
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        data = response.json()
        ids = [t["id"] for t in data["tasks"]]
        # Overdue first, then due today, then in_progress, then backlog
        assert ids.index("s3") < ids.index("s4")  # overdue < due_today
        assert ids.index("s4") < ids.index("s2")  # due_today < in_progress
        assert ids.index("s2") < ids.index("s1")  # in_progress < plain backlog

    def test_rollover_auto_select_flag(self, client):
        """in_progress and overdue/due_today tasks are auto-selected."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status, deadline)
               VALUES
               ('a1', '2026-02-05', 'In progress', 'in_progress', NULL),
               ('a2', '2026-02-05', 'Overdue', 'backlog', '2026-02-08'),
               ('a3', '2026-02-05', 'Due today', 'backlog', '2026-02-10'),
               ('a4', '2026-02-05', 'Plain backlog', 'backlog', NULL),
               ('a5', '2026-02-05', 'Upcoming', 'backlog', '2026-02-15')
            """
        )
        response = client.get("/tasks/rollover?target_date=2026-02-10")
        data = response.json()
        tasks_by_id = {t["id"]: t for t in data["tasks"]}

        assert tasks_by_id["a1"]["auto_select"] is True   # in_progress
        assert tasks_by_id["a2"]["auto_select"] is True   # overdue
        assert tasks_by_id["a3"]["auto_select"] is True   # due_today
        assert tasks_by_id["a4"]["auto_select"] is False   # plain backlog
        assert tasks_by_id["a5"]["auto_select"] is False   # upcoming, not in_progress

    def test_rollover_commit_updates_source_file(self, client):
        """POST /tasks/rollover updates source_file for selected tasks."""
        from src.main import app

        db = app.state.db
        db.execute(
            """INSERT INTO tasks (id, date, description, status, source_file)
               VALUES
               ('c1', '2026-02-05', 'Task 1', 'backlog', 'Daily-Notes/2026-02/2026-02-05.md'),
               ('c2', '2026-02-05', 'Task 2', 'backlog', 'Daily-Notes/2026-02/2026-02-05.md'),
               ('c3', '2026-02-05', 'Task 3', 'backlog', 'Daily-Notes/2026-02/2026-02-05.md')
            """
        )
        response = client.post("/tasks/rollover", json={
            "task_ids": ["c1", "c2"],
            "new_source_file": "Daily-Notes/2026-02/2026-02-10.md",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 2

        # Verify source_file was updated for c1 and c2 but not c3
        result = db.execute("SELECT id, source_file FROM tasks WHERE id IN ('c1', 'c2', 'c3') ORDER BY id")
        rows = {row[0]: row[1] for row in result.fetchall()}
        assert rows["c1"] == "Daily-Notes/2026-02/2026-02-10.md"
        assert rows["c2"] == "Daily-Notes/2026-02/2026-02-10.md"
        assert rows["c3"] == "Daily-Notes/2026-02/2026-02-05.md"

    def test_rollover_commit_empty_list(self, client):
        """POST /tasks/rollover with empty list returns 0 updated."""
        response = client.post("/tasks/rollover", json={
            "task_ids": [],
            "new_source_file": "Daily-Notes/2026-02/2026-02-10.md",
        })
        assert response.status_code == 200
        assert response.json()["updated"] == 0

    def test_rollover_invalid_date(self, client):
        """Invalid date format returns 400."""
        response = client.get("/tasks/rollover?target_date=bad-date")
        assert response.status_code == 400
