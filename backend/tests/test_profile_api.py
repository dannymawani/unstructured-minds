"""Tests for life profile API endpoints."""

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
             patch("src.api.settings.settings", mock_settings), \
             patch("src.api.profile.settings", mock_settings), \
             patch("src.api.profile.PROFILE_FILE", tmp_path / "data" / "life_profile.json"):
            yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    from src.main import app
    with TestClient(app) as client:
        yield client


class TestGetProfile:
    """Tests for GET /profile endpoint."""

    def test_returns_default_profile(self, client):
        """Test that a default empty profile is returned when none exists."""
        response = client.get("/profile")

        assert response.status_code == 200
        data = response.json()
        assert "overview" in data
        assert "personal" in data
        assert "work" in data
        assert "training" in data
        assert "goals" in data

    def test_default_profile_has_empty_fields(self, client):
        """Test that default profile fields are empty."""
        response = client.get("/profile")

        data = response.json()
        assert data["overview"]["name"] == ""
        assert data["personal"]["family"] == []
        assert data["work"]["projects"] == []
        assert data["training"]["disciplines"] == []
        assert data["goals"] == []


class TestUpdateProfile:
    """Tests for PUT /profile endpoint."""

    def test_update_full_profile(self, client):
        """Test updating the full profile."""
        profile = {
            "overview": {
                "name": "Danny",
                "age": 30,
                "location": "Oslo",
                "company": "Tech Corp",
                "role": "Engineer",
                "summary": "Software engineer",
            },
            "personal": {
                "family": ["Partner"],
                "friends": ["Alice"],
                "interests": ["Climbing"],
                "patterns": ["Morning person"],
                "notes": "",
            },
            "work": {
                "role": "Senior Engineer",
                "company": "Tech Corp",
                "projects": ["Project X"],
                "colleagues": ["Bob"],
                "skills": ["Python"],
                "notes": "",
            },
            "training": {
                "disciplines": ["Powerlifting"],
                "current_lifts": {"squat": "180kg"},
                "recovery": "Good",
                "goals": ["200kg squat"],
                "notes": "",
            },
            "goals": [
                {
                    "id": "g1",
                    "category": "fitness",
                    "description": "Squat 200kg",
                    "status": "active",
                    "target_date": "2026-06-01",
                    "progress": 50,
                }
            ],
        }

        response = client.put("/profile", json=profile)
        assert response.status_code == 200
        data = response.json()
        assert data["overview"]["name"] == "Danny"
        assert data["training"]["current_lifts"]["squat"] == "180kg"

    def test_profile_persists(self, client):
        """Test that profile data persists across requests."""
        profile = {
            "overview": {"name": "Test User", "age": None, "location": "", "company": "", "role": "", "summary": ""},
            "personal": {"family": [], "friends": [], "interests": [], "patterns": [], "notes": ""},
            "work": {"role": "", "company": "", "projects": [], "colleagues": [], "skills": [], "notes": ""},
            "training": {"disciplines": [], "current_lifts": {}, "recovery": "", "goals": [], "notes": ""},
            "goals": [],
        }
        client.put("/profile", json=profile)

        response = client.get("/profile")
        assert response.json()["overview"]["name"] == "Test User"


class TestPatchSection:
    """Tests for PATCH /profile/{section} endpoint."""

    def test_patch_overview(self, client):
        """Test patching the overview section."""
        response = client.patch(
            "/profile/overview",
            json={"name": "Updated Name", "age": 31, "location": "Bergen", "company": "", "role": "", "summary": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overview"]["name"] == "Updated Name"

    def test_patch_goals(self, client):
        """Test patching the goals section."""
        goals = [
            {"id": "g1", "category": "health", "description": "Sleep 8h", "status": "active", "target_date": None, "progress": 0}
        ]
        response = client.patch("/profile/goals", json=goals)

        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 1
        assert data["goals"][0]["description"] == "Sleep 8h"

    def test_patch_invalid_section(self, client):
        """Test that invalid section returns 400."""
        response = client.patch("/profile/invalid", json={"foo": "bar"})
        assert response.status_code == 400

    def test_patch_preserves_other_sections(self, client):
        """Test that patching one section doesn't affect others."""
        # Set up profile
        profile = {
            "overview": {"name": "Danny", "age": None, "location": "", "company": "", "role": "", "summary": ""},
            "personal": {"family": ["Partner"], "friends": [], "interests": [], "patterns": [], "notes": ""},
            "work": {"role": "", "company": "", "projects": [], "colleagues": [], "skills": [], "notes": ""},
            "training": {"disciplines": [], "current_lifts": {}, "recovery": "", "goals": [], "notes": ""},
            "goals": [],
        }
        client.put("/profile", json=profile)

        # Patch only overview
        client.patch("/profile/overview", json={"name": "Updated", "age": None, "location": "", "company": "", "role": "", "summary": ""})

        # Personal section should be unchanged
        response = client.get("/profile")
        assert response.json()["personal"]["family"] == ["Partner"]


class TestReviewsCRUD:
    """Tests for progress review CRUD endpoints."""

    def _create_review(self, client) -> dict:
        """Helper to create a review."""
        return client.post(
            "/profile/reviews",
            json={
                "period_start": "2026-01-20",
                "period_end": "2026-02-02",
                "key_wins": ["Shipped feature X"],
                "challenges": ["Tight deadline"],
                "work_highlights": "Delivered on time",
                "training_summary": "Hit PR on squat",
                "personal_wins": ["Read a book"],
                "health_metrics": {"avg_sleep": 7.5},
                "goal_progress": {"g1": 60},
                "focus_next": ["Start project Y"],
            },
        ).json()

    def test_create_review(self, client):
        """Test creating a progress review."""
        response = client.post(
            "/profile/reviews",
            json={
                "period_start": "2026-01-20",
                "period_end": "2026-02-02",
                "key_wins": ["Shipped feature X"],
                "challenges": [],
                "work_highlights": "",
                "training_summary": "",
                "personal_wins": [],
                "focus_next": [],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["period_start"] == "2026-01-20"
        assert data["key_wins"] == ["Shipped feature X"]
        assert "id" in data
        assert "created_at" in data

    def test_list_reviews(self, client):
        """Test listing reviews returns newest first."""
        # Create two reviews
        client.post(
            "/profile/reviews",
            json={
                "period_start": "2026-01-06",
                "period_end": "2026-01-19",
                "key_wins": ["First"],
                "challenges": [],
                "work_highlights": "",
                "training_summary": "",
                "personal_wins": [],
                "focus_next": [],
            },
        )
        client.post(
            "/profile/reviews",
            json={
                "period_start": "2026-01-20",
                "period_end": "2026-02-02",
                "key_wins": ["Second"],
                "challenges": [],
                "work_highlights": "",
                "training_summary": "",
                "personal_wins": [],
                "focus_next": [],
            },
        )

        response = client.get("/profile/reviews")
        assert response.status_code == 200
        reviews = response.json()
        assert len(reviews) == 2
        # Newest first
        assert reviews[0]["key_wins"] == ["Second"]

    def test_get_review(self, client):
        """Test getting a single review by ID."""
        created = self._create_review(client)

        response = client.get(f"/profile/reviews/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_review_not_found(self, client):
        """Test 404 for missing review."""
        response = client.get("/profile/reviews/nonexistent")
        assert response.status_code == 404

    def test_update_review(self, client):
        """Test updating a review."""
        created = self._create_review(client)

        response = client.put(
            f"/profile/reviews/{created['id']}",
            json={"key_wins": ["Updated win"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key_wins"] == ["Updated win"]
        # Other fields should be unchanged
        assert data["challenges"] == ["Tight deadline"]

    def test_update_review_not_found(self, client):
        """Test 404 for updating missing review."""
        response = client.put(
            "/profile/reviews/nonexistent",
            json={"key_wins": ["nope"]},
        )
        assert response.status_code == 404

    def test_delete_review(self, client):
        """Test deleting a review."""
        created = self._create_review(client)

        response = client.delete(f"/profile/reviews/{created['id']}")
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(f"/profile/reviews/{created['id']}")
        assert response.status_code == 404

    def test_delete_review_not_found(self, client):
        """Test 404 for deleting missing review."""
        response = client.delete("/profile/reviews/nonexistent")
        assert response.status_code == 404
