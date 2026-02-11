"""Tests for skills module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.skills import DailyNoteSkill, SkillContext, SkillRegistry, get_default_registry


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


@pytest.fixture
def mock_storage():
    """Create mock storage backend."""
    storage = MagicMock()
    storage.exists = AsyncMock(return_value=False)
    storage.write = AsyncMock()
    return storage


class TestDailyNoteSkill:
    """Tests for DailyNoteSkill."""

    def test_skill_properties(self):
        """Test skill name and description."""
        skill = DailyNoteSkill()
        assert skill.name == "daily"
        assert "daily note" in skill.description.lower()

    @pytest.mark.asyncio
    async def test_creates_daily_note(self, mock_storage):
        """Test creating a daily note."""
        skill = DailyNoteSkill()
        context = SkillContext(storage=mock_storage, current_date="2026-02-02")

        result = await skill.execute(context)

        assert result.success
        assert result.file_path == "2026/02/2026-02-02-daily-note.md"
        mock_storage.write.assert_called_once()
        content = mock_storage.write.call_args[0][1].decode("utf-8")
        assert "## 🎯 Today's Focus" in content
        assert "## 💼 Work" in content

    @pytest.mark.asyncio
    async def test_uses_today_when_no_date(self, mock_storage):
        """Test using today's date when not specified."""
        skill = DailyNoteSkill()
        context = SkillContext(storage=mock_storage)

        result = await skill.execute(context)

        assert result.success
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in result.file_path

    @pytest.mark.asyncio
    async def test_reports_existing_note(self, mock_storage):
        """Test behavior when note already exists."""
        mock_storage.exists = AsyncMock(return_value=True)
        skill = DailyNoteSkill()
        context = SkillContext(storage=mock_storage, current_date="2026-02-02")

        result = await skill.execute(context)

        assert result.success
        assert "already exists" in result.message
        mock_storage.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, mock_storage):
        """Test error on invalid date format."""
        skill = DailyNoteSkill()
        context = SkillContext(storage=mock_storage, current_date="02-02-2026")

        result = await skill.execute(context)

        assert not result.success
        assert "Invalid date format" in result.message


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    def test_register_and_get(self):
        """Test registering and retrieving skills."""
        registry = SkillRegistry()
        skill = DailyNoteSkill()

        registry.register(skill)

        assert registry.get("daily") is skill
        assert registry.get("nonexistent") is None

    def test_list_skills(self):
        """Test listing all skills."""
        registry = SkillRegistry()
        registry.register(DailyNoteSkill())

        skills = registry.list()

        assert len(skills) == 1
        assert skills[0]["name"] == "daily"

    @pytest.mark.asyncio
    async def test_execute_skill(self, mock_storage):
        """Test executing a skill through registry."""
        registry = SkillRegistry()
        registry.register(DailyNoteSkill())
        context = SkillContext(storage=mock_storage, current_date="2026-02-02")

        result = await registry.execute("daily", context)

        assert result.success

    @pytest.mark.asyncio
    async def test_execute_unknown_skill(self, mock_storage):
        """Test error when executing unknown skill."""
        registry = SkillRegistry()
        context = SkillContext(storage=mock_storage)

        with pytest.raises(KeyError):
            await registry.execute("unknown", context)


class TestDefaultRegistry:
    """Tests for default skill registry."""

    def test_has_daily_skill(self):
        """Test that default registry has daily skill."""
        registry = get_default_registry()
        assert registry.get("daily") is not None


class TestSkillsAPI:
    """Tests for skills API endpoints."""

    def test_list_skills(self, client):
        """Test listing available skills."""
        response = client.get("/skills")

        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        skill_names = [s["name"] for s in data["skills"]]
        assert "daily" in skill_names

    def test_execute_daily_skill(self, client):
        """Test executing daily skill via API."""
        response = client.post(
            "/skills/execute",
            json={"skill": "daily", "date": "2026-02-02"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "2026/02/2026-02-02-daily-note.md" in data["file_path"]

    def test_execute_unknown_skill(self, client):
        """Test error when executing unknown skill."""
        response = client.post(
            "/skills/execute",
            json={"skill": "unknown"},
        )

        assert response.status_code == 404

    def test_execute_daily_skill_no_date(self, client):
        """Test executing daily skill without date."""
        response = client.post(
            "/skills/execute",
            json={"skill": "daily"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in data["file_path"]
