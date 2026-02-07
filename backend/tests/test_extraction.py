"""Tests for extraction module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.extraction import EXTRACTION_SCHEMAS, get_schema, ExtractionPipeline, ExtractionResult


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


class MockResult:
    """Mock database result."""
    def __init__(self, data=None):
        self._data = data or []

    def fetchall(self):
        return self._data

    def fetchone(self):
        return self._data[0] if self._data else None


@pytest.fixture
def mock_db():
    """Create mock database manager."""
    db = MagicMock()
    db.execute = MagicMock(return_value=MockResult([]))
    return db


@pytest.fixture
def mock_claude():
    """Create mock Claude client."""
    claude = MagicMock()
    claude.is_configured = True
    claude.extract = AsyncMock(return_value={
        "date": "2026-02-02",
        "daily_metrics": {
            "sleep_hours": 7.5,
            "energy": 8,
            "mood": 7,
        },
        "activities": [
            {
                "activity_type": "strength",
                "duration_minutes": 60,
                "exercises": [
                    {"name": "Squat", "weight_kg": 100, "reps": 5, "sets": 3},
                ],
            }
        ],
        "tasks": [
            {"description": "Review PRs", "status": "done"},
        ],
        "meals": [],
    })
    return claude


class TestSchemas:
    """Tests for extraction schemas."""

    def test_schemas_available(self):
        """Test that expected schemas are available."""
        assert "exercise" in EXTRACTION_SCHEMAS
        assert "daily_metrics" in EXTRACTION_SCHEMAS
        assert "tasks" in EXTRACTION_SCHEMAS
        assert "food_log" in EXTRACTION_SCHEMAS
        assert "combined" in EXTRACTION_SCHEMAS

    def test_get_schema_returns_schema(self):
        """Test getting a schema by name."""
        schema = get_schema("combined")
        assert "properties" in schema
        assert "date" in schema["properties"]

    def test_get_schema_raises_on_unknown(self):
        """Test error on unknown schema."""
        with pytest.raises(KeyError):
            get_schema("unknown")

    def test_combined_schema_has_all_fields(self):
        """Test combined schema includes all extraction types."""
        schema = get_schema("combined")
        props = schema["properties"]
        assert "date" in props
        assert "daily_metrics" in props
        assert "activities" in props
        assert "tasks" in props
        assert "meals" in props


class TestExtractionPipeline:
    """Tests for ExtractionPipeline."""

    def test_compute_hash(self, mock_db):
        """Test content hashing."""
        pipeline = ExtractionPipeline(mock_db)
        hash1 = pipeline._compute_hash("content")
        hash2 = pipeline._compute_hash("content")
        hash3 = pipeline._compute_hash("different")

        assert hash1 == hash2
        assert hash1 != hash3

    def test_extract_date_from_path(self, mock_db):
        """Test date extraction from file path."""
        pipeline = ExtractionPipeline(mock_db)

        assert pipeline._extract_date_from_path("Daily-Notes/2026-02/2026-02-02.md") == "2026-02-02"
        assert pipeline._extract_date_from_path("notes/2026-01-15.md") == "2026-01-15"
        assert pipeline._extract_date_from_path("random-note.md") is None

    @pytest.mark.asyncio
    async def test_extract_without_claude(self, mock_db):
        """Test extraction fails without Claude."""
        pipeline = ExtractionPipeline(mock_db, claude=None)

        result = await pipeline.extract("test.md", "content")

        assert not result.success
        assert "not configured" in result.error

    @pytest.mark.asyncio
    async def test_extract_with_claude(self, mock_db, mock_claude):
        """Test successful extraction with Claude."""
        pipeline = ExtractionPipeline(mock_db, mock_claude)

        result = await pipeline.extract("Daily-Notes/2026-02/2026-02-02.md", "# Test")

        assert result.success
        assert result.data is not None
        assert result.data["date"] == "2026-02-02"
        mock_claude.extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_stores_data(self, mock_db, mock_claude):
        """Test that extraction stores data in database."""
        pipeline = ExtractionPipeline(mock_db, mock_claude)

        result = await pipeline.extract("test.md", "# Test")

        assert result.success
        # Verify database writes were called
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_extract_logs_success(self, mock_db, mock_claude):
        """Test successful extraction is logged."""
        pipeline = ExtractionPipeline(mock_db, mock_claude)

        await pipeline.extract("test.md", "# Test")

        # Check that extraction was logged
        calls = [str(c) for c in mock_db.execute.call_args_list]
        assert any("extraction_log" in str(c) for c in calls)

    @pytest.mark.asyncio
    async def test_skip_if_already_extracted(self, mock_db, mock_claude):
        """Test skipping extraction if file unchanged."""
        # Compute the hash for the content we'll use
        content_hash = ExtractionPipeline(mock_db)._compute_hash("content")
        # Simulate file already extracted
        mock_db.execute = MagicMock(return_value=MockResult([
            (content_hash,)
        ]))
        pipeline = ExtractionPipeline(mock_db, mock_claude)

        result = await pipeline.extract("test.md", "content", force=False)

        assert result.success
        assert "Already extracted" in result.error
        mock_claude.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_re_extraction(self, mock_db, mock_claude):
        """Test forcing re-extraction."""
        content_hash = ExtractionPipeline(mock_db)._compute_hash("content")

        # Return different results depending on the query:
        # - extraction_log queries get the hash tuple
        # - task/data queries get empty results
        def smart_execute(sql, params=None):
            if "extraction_log" in sql:
                return MockResult([(content_hash,)])
            return MockResult([])

        mock_db.execute = MagicMock(side_effect=smart_execute)
        pipeline = ExtractionPipeline(mock_db, mock_claude)

        result = await pipeline.extract("test.md", "content", force=True)

        assert result.success
        mock_claude.extract.assert_called_once()


class TestExtractionAPI:
    """Tests for extraction API endpoints."""

    def test_extract_file_not_found(self, client):
        """Test extraction of non-existent file."""
        response = client.post(
            "/extract",
            json={"file_path": "nonexistent.md"},
        )

        assert response.status_code == 404

    def test_extract_requires_claude(self, client, test_settings):
        """Test extraction requires Claude configuration."""
        # Create a test file
        test_file = test_settings.vault_path / "test.md"
        test_file.write_text("# Test")

        response = client.post(
            "/extract",
            json={"file_path": "test.md"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should fail because Claude is not configured in test
        assert not data["success"]
        assert "not configured" in data["message"]

    def test_extract_batch_endpoint_exists(self, client):
        """Test batch extraction endpoint exists."""
        response = client.post(
            "/extract/batch",
            json={"file_paths": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["successful"] == 0
        assert data["failed"] == 0
