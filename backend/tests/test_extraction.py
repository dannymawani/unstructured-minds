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
                    {"name": "Squat", "sets": [
                        {"weight_kg": 100, "reps": 5},
                        {"weight_kg": 100, "reps": 5},
                        {"weight_kg": 100, "reps": 5},
                    ]},
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

    def test_extract_requires_claude(self, test_settings):
        """Test extraction requires Claude configuration."""
        from src.main import app
        from src.api.extraction import get_claude

        # Override Claude dependency to return unconfigured client
        unconfigured = MagicMock()
        unconfigured.is_configured = False
        app.dependency_overrides[get_claude] = lambda: unconfigured

        try:
            with TestClient(app) as cl:
                test_file = test_settings.vault_path / "test.md"
                test_file.write_text("# Test")

                response = cl.post(
                    "/extract",
                    json={"file_path": "test.md"},
                )

                assert response.status_code == 200
                data = response.json()
                assert not data["success"]
                assert "not configured" in data["message"]
        finally:
            app.dependency_overrides.pop(get_claude, None)

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


class TestStripSuggestions:
    """Tests for _strip_suggestions method."""

    def test_strips_suggested_workout_with_table(self, mock_db):
        """Test that suggested workout tables with blockquotes are stripped."""
        pipeline = ExtractionPipeline(mock_db)
        content = """## Workout
- **Type**: Strength
- **Focus**: Upper Body

> **Suggested Workout (from 2026-02-10)** — edit below to log
> 
> | Exercise | Last | Suggested | Reps | Sets |
> |----------|------|-----------|------|------|
> | Squat | 100kg | 102.5kg | 5 | 3 |

### Actual workout
- Bench Press: 80kg x 5 x 3
- Deadlift: 120kg x 3 x 3"""

        result = pipeline._strip_suggestions(content)
        
        assert "| Squat |" not in result
        assert "Suggested Workout" not in result
        assert "Bench Press" in result
        assert "Deadlift" in result

    def test_strips_old_format_suggestion(self, mock_db):
        """Test stripping old-format 'Last session' blockquote tables."""
        pipeline = ExtractionPipeline(mock_db)
        content = """> **Last session (2026-02-08)** — edit below
> 
> | Exercise | Last | Suggested | Reps | Sets |
> |----------|------|-----------|------|------|
> | Row | 60kg | 62.5kg | 8 | 3 |

### My workout
- Pull-ups: BW x 10 x 3"""

        result = pipeline._strip_suggestions(content)
        
        assert "| Row |" not in result
        assert "Last session" not in result
        assert "Pull-ups" in result

    def test_preserves_non_table_blockquotes(self, mock_db):
        """Test that blockquotes without tables are preserved."""
        pipeline = ExtractionPipeline(mock_db)
        content = """> This is a regular blockquote with no table
> Just some text here

### Notes
- Something important"""

        result = pipeline._strip_suggestions(content)
        
        assert "regular blockquote" in result
        assert "Just some text here" in result
        assert "Something important" in result

    def test_strips_ai_generated_header_variant(self, mock_db):
        """Test stripping AI-generated 'Suggested Workout' header variant."""
        pipeline = ExtractionPipeline(mock_db)
        content = """> **Suggested Workout**
> 
> | Exercise | Weight | Reps | Sets |
> |----------|--------|------|------|
> | Turkish Get-Up | 16kg | 3 | 3 |

Actual exercises:
- Leg Curl 40kg 3x12"""

        result = pipeline._strip_suggestions(content)
        
        assert "Turkish Get-Up" not in result
        assert "Suggested Workout" not in result
        assert "Leg Curl" in result

    def test_handles_content_without_blockquotes(self, mock_db):
        """Test handling of content with no blockquotes."""
        pipeline = ExtractionPipeline(mock_db)
        content = """## My Workout
- Squat: 100kg x 5 x 3
- Bench: 80kg x 5 x 3"""

        result = pipeline._strip_suggestions(content)
        
        assert result == content

    def test_handles_multiple_blockquote_blocks(self, mock_db):
        """Test handling multiple blockquote blocks."""
        pipeline = ExtractionPipeline(mock_db)
        content = """> Regular blockquote
> Just notes

> **Suggested Workout**
> 
> | Exercise | Reps |
> |----------|------|
> | Squat | 5 |

> Another blockquote
> More notes

## Actual exercises
- Deadlift: 120kg"""

        result = pipeline._strip_suggestions(content)
        
        # Regular blockquotes should stay
        assert "Regular blockquote" in result
        assert "Another blockquote" in result
        # Suggested workout should be stripped
        assert "| Squat |" not in result
        # Actual data should stay
        assert "Deadlift" in result

    def test_empty_content(self, mock_db):
        """Test handling of empty content."""
        pipeline = ExtractionPipeline(mock_db)
        
        result = pipeline._strip_suggestions("")
        assert result == ""

    def test_blockquote_at_end_of_content(self, mock_db):
        """Test blockquote at end of file without trailing newline."""
        pipeline = ExtractionPipeline(mock_db)
        content = """## Workout

> **Suggested Workout**
> | Exercise | Reps |
> |----------|------|
> | Squat | 5 |"""

        result = pipeline._strip_suggestions(content)
        
        assert "| Squat |" not in result
