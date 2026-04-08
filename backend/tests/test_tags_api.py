"""Tests for tags API endpoints."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import src.main


@pytest.fixture
def test_settings(tmp_path: Path):
    """Create test settings with temp paths."""
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

    with patch.object(src.main, "settings", mock_settings):
        yield mock_settings


@pytest.fixture
def client(test_settings):
    """Create test client with mocked settings."""
    with TestClient(src.main.app) as client:
        yield client


class TestListTags:
    """Tests for GET /tags endpoint."""

    def test_returns_empty_list_when_no_files(self, client: TestClient) -> None:
        """Test returns empty list when vault is empty."""
        response = client.get("/tags")
        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == []
        assert data["total"] == 0

    def test_returns_tags_with_counts(self, client: TestClient, test_settings) -> None:
        """Test returns tags with occurrence counts."""
        vault_path = test_settings.vault_path
        (vault_path / "note1.md").write_text("# Note 1\n\n#project #todo")
        (vault_path / "note2.md").write_text("# Note 2\n\n#project #done")

        response = client.get("/tags")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # project, todo, done

        # Find the project tag
        project_tag = next(t for t in data["tags"] if t["tag"] == "project")
        assert project_tag["count"] == 2

    def test_tags_sorted_by_count_then_name(self, client: TestClient, test_settings) -> None:
        """Test tags are sorted by count (descending) then name."""
        vault_path = test_settings.vault_path
        (vault_path / "note1.md").write_text("#alpha #beta")
        (vault_path / "note2.md").write_text("#beta #gamma")
        (vault_path / "note3.md").write_text("#beta")

        response = client.get("/tags")
        assert response.status_code == 200
        data = response.json()

        # beta should be first (count=3), then alpha and gamma (count=1 each, sorted alphabetically)
        assert data["tags"][0]["tag"] == "beta"
        assert data["tags"][0]["count"] == 3

    def test_ignores_non_markdown_files(self, client: TestClient, test_settings) -> None:
        """Test only markdown files are scanned."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("#real-tag")
        (vault_path / "data.json").write_text('{"tag": "#fake-tag"}')

        response = client.get("/tags")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["tags"][0]["tag"] == "real-tag"


class TestGetNotesByTag:
    """Tests for GET /tags/{tag}/notes endpoint."""

    def test_returns_notes_with_tag(self, client: TestClient, test_settings) -> None:
        """Test returns notes containing the specified tag."""
        vault_path = test_settings.vault_path
        (vault_path / "note1.md").write_text("# Note One\n\n#project")
        (vault_path / "note2.md").write_text("# Note Two\n\n#project")
        (vault_path / "note3.md").write_text("# Note Three\n\n#other")

        response = client.get("/tags/project/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["tag"] == "project"
        assert data["count"] == 2
        assert len(data["notes"]) == 2

    def test_returns_empty_for_unknown_tag(self, client: TestClient, test_settings) -> None:
        """Test returns empty list for tag that doesn't exist."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# Note\n\n#other")

        response = client.get("/tags/nonexistent/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["notes"] == []

    def test_extracts_title_from_h1(self, client: TestClient, test_settings) -> None:
        """Test note title is extracted from H1 heading."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# My Custom Title\n\n#project")

        response = client.get("/tags/project/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["notes"][0]["title"] == "My Custom Title"

    def test_title_fallback_to_filename(self, client: TestClient, test_settings) -> None:
        """Test falls back to filename when no H1 heading."""
        vault_path = test_settings.vault_path
        (vault_path / "my-note.md").write_text("Content with #project tag")

        response = client.get("/tags/project/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["notes"][0]["title"] == "my-note"


class TestGetBacklinks:
    """Tests for GET /tags/links/backlinks endpoint."""

    def test_finds_backlinks(self, client: TestClient, test_settings) -> None:
        """Test finds notes that link to the target."""
        vault_path = test_settings.vault_path
        (vault_path / "target.md").write_text("# Target Note\n\nContent.")
        (vault_path / "source1.md").write_text("# Source 1\n\nLink to [[target]].")
        (vault_path / "source2.md").write_text("# Source 2\n\nAnother link to [[target]].")
        (vault_path / "other.md").write_text("# Other\n\nNo links here.")

        response = client.get("/tags/links/backlinks?path=target.md")
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "target.md"
        assert data["count"] == 2
        assert len(data["backlinks"]) == 2

    def test_returns_empty_for_no_backlinks(self, client: TestClient, test_settings) -> None:
        """Test returns empty list when no backlinks exist."""
        vault_path = test_settings.vault_path
        (vault_path / "lonely.md").write_text("# Lonely Note\n\nNo one links here.")

        response = client.get("/tags/links/backlinks?path=lonely.md")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["backlinks"] == []

    def test_excludes_self_links(self, client: TestClient, test_settings) -> None:
        """Test a note linking to itself is not counted."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# Note\n\nLink to [[note]].")

        response = client.get("/tags/links/backlinks?path=note.md")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0

    def test_matches_by_filename(self, client: TestClient, test_settings) -> None:
        """Test matching works with filename-only links."""
        vault_path = test_settings.vault_path
        folder = vault_path / "folder"
        folder.mkdir()
        (folder / "target.md").write_text("# Target\n\nContent.")
        (vault_path / "source.md").write_text("# Source\n\nLink to [[target]].")

        response = client.get("/tags/links/backlinks?path=folder/target.md")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1


class TestGetOutgoingLinks:
    """Tests for GET /tags/links/outgoing endpoint."""

    def test_returns_outgoing_links(self, client: TestClient, test_settings) -> None:
        """Test returns all wiki links from a note."""
        vault_path = test_settings.vault_path
        (vault_path / "source.md").write_text(
            "# Source\n\n"
            "Links to [[Note A]] and [[Note B]].\n"
            "Also [[folder/Note C]]."
        )

        response = client.get("/tags/links/outgoing?path=source.md")
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "source.md"
        assert data["count"] == 3
        assert set(data["links"]) == {"Note A", "Note B", "folder/Note C"}

    def test_returns_empty_for_no_links(self, client: TestClient, test_settings) -> None:
        """Test returns empty list when note has no outgoing links."""
        vault_path = test_settings.vault_path
        (vault_path / "note.md").write_text("# Note\n\nNo links here.")

        response = client.get("/tags/links/outgoing?path=note.md")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["links"] == []

    def test_returns_empty_for_nonexistent_file(self, client: TestClient, test_settings) -> None:
        """Test returns empty list for file that doesn't exist."""
        response = client.get("/tags/links/outgoing?path=nonexistent.md")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["links"] == []
