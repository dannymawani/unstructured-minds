"""Tests for search API endpoint."""

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


class TestSearchEndpoint:
    """Tests for search endpoint."""

    def test_search_empty_query_returns_empty(self, client: TestClient) -> None:
        """Test search with empty query returns no results."""
        response = client.post("/search", json={"query": "", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_no_files_returns_empty(self, client: TestClient) -> None:
        """Test search with no files returns empty results."""
        response = client.post("/search", json={"query": "test", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    def test_search_finds_matching_content(self, client: TestClient, test_settings) -> None:
        """Test search finds files with matching content."""
        vault_path = test_settings.vault_path
        (vault_path / "test.md").write_text("# Hello World\n\nThis is a test file about exercise.")

        response = client.post("/search", json={"query": "exercise", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["path"] == "test.md"
        assert "exercise" in data["results"][0]["snippet"].lower()

    def test_search_returns_snippet_with_context(self, client: TestClient, test_settings) -> None:
        """Test search returns snippets with matching context."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text(
            "# Daily Note\n\n"
            "Today I did some exercises.\n"
            "I ran 5 miles and did 50 pushups.\n"
            "Feeling great!"
        )

        response = client.post("/search", json={"query": "pushups", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert "pushups" in data["results"][0]["snippet"].lower()

    def test_search_respects_limit(self, client: TestClient, test_settings) -> None:
        """Test search respects limit parameter."""
        vault_path = test_settings.vault_path
        for i in range(10):
            (vault_path / f"note{i}.md").write_text(f"# Note {i}\n\nThis note contains test content.")

        response = client.post("/search", json={"query": "test", "limit": 3})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 3

    def test_search_case_insensitive(self, client: TestClient, test_settings) -> None:
        """Test search is case insensitive."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# Note\n\nSQUAT is an exercise.")

        response = client.post("/search", json={"query": "squat", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1

    def test_search_multiple_terms(self, client: TestClient, test_settings) -> None:
        """Test search with multiple terms."""
        vault_path = test_settings.vault_path
        (vault_path / "note1.md").write_text("# Note 1\n\nDid squat exercises today.")
        (vault_path / "note2.md").write_text("# Note 2\n\nJust squats, no deadlifts.")
        (vault_path / "note3.md").write_text("# Note 3\n\nNo relevant content here.")

        response = client.post("/search", json={"query": "squat exercises", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        # Should find notes with either term, ranked by coverage
        assert len(data["results"]) >= 1

    def test_search_returns_title(self, client: TestClient, test_settings) -> None:
        """Test search returns title from H1 heading."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# My Custom Title\n\nSome searchable content.")

        response = client.post("/search", json={"query": "searchable", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["title"] == "My Custom Title"

    def test_search_title_fallback_to_filename(self, client: TestClient, test_settings) -> None:
        """Test search falls back to filename when no H1 heading."""
        vault_path = test_settings.vault_path
        (vault_path / "my-note.md").write_text("Some searchable content without heading.")

        response = client.post("/search", json={"query": "searchable", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["title"] == "my-note"

    def test_search_returns_score(self, client: TestClient, test_settings) -> None:
        """Test search returns relevance score."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# Note\n\nTest content with test word repeated test.")

        response = client.post("/search", json={"query": "test", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert "score" in data["results"][0]
        assert 0 <= data["results"][0]["score"] <= 1

    def test_search_sorts_by_score(self, client: TestClient, test_settings) -> None:
        """Test search results are sorted by score descending."""
        vault_path = test_settings.vault_path
        # Create files with different numbers of matches
        (vault_path / "few.md").write_text("# Few\n\nOne exercise.")
        (vault_path / "many.md").write_text(
            "# Many\n\nExercise exercise exercise exercise exercise!"
        )

        response = client.post("/search", json={"query": "exercise", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        # Many matches should score higher
        assert data["results"][0]["score"] >= data["results"][1]["score"]

    def test_search_only_searches_markdown_files(self, client: TestClient, test_settings) -> None:
        """Test search only searches markdown files."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# Note\n\nSearchable content.")
        (vault_path / "data.json").write_text('{"content": "Searchable content"}')

        response = client.post("/search", json={"query": "Searchable", "limit": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["path"] == "note.md"
