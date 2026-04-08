"""Tests for Claude API client."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import anthropic

from src.claude.client import ClaudeClient


class TestClaudeClientInit:
    """Tests for ClaudeClient initialization."""

    def test_client_init_with_api_key(self) -> None:
        """Test client initializes with provided API key."""
        client = ClaudeClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model_fast == "claude-haiku-4-5-20251001"
        assert client.model_smart == "claude-sonnet-4-5-20250929"

    def test_client_init_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test client uses environment variable."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        client = ClaudeClient()
        assert client.api_key == "env-key"

    def test_is_configured_with_key(self) -> None:
        """Test is_configured returns True when API key set."""
        client = ClaudeClient(api_key="test-key")
        assert client.is_configured is True

    def test_is_configured_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_configured returns False without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = ClaudeClient()
        assert client.is_configured is False

    def test_client_property_raises_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test accessing client raises error without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = ClaudeClient()
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not configured"):
            _ = client.client


class TestClaudeClientExtraction:
    """Tests for extraction functionality."""

    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch("src.claude.client.Anthropic") as mock:
            yield mock

    async def test_extraction_returns_json(self, mock_anthropic: MagicMock) -> None:
        """Test extraction parses tool use response."""
        # Set up mock response with tool use
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.input = {"exercise_log": [{"name": "squat", "weight_kg": 100}]}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]

        mock_anthropic.return_value.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        result = await client.extract("# Test content", {"type": "object"})

        assert "exercise_log" in result
        assert result["exercise_log"][0]["name"] == "squat"

    async def test_extraction_calls_with_tool(self, mock_anthropic: MagicMock) -> None:
        """Test extraction passes tool to API."""
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.input = {}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]

        mock_anthropic.return_value.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        await client.extract("content", schema)

        call_kwargs = mock_anthropic.return_value.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"][0]["name"] == "extract_data"


class TestClaudeClientQuery:
    """Tests for query functionality."""

    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch("src.claude.client.Anthropic") as mock:
            yield mock

    async def test_query_returns_text(self, mock_anthropic: MagicMock) -> None:
        """Test query returns response text."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "You did 5 workouts this week."

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        mock_anthropic.return_value.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        result = await client.query("How many workouts?", "workout data here")

        assert result == "You did 5 workouts this week."

    async def test_query_uses_fast_model(self, mock_anthropic: MagicMock) -> None:
        """Test query uses the fast model."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "answer"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        mock_anthropic.return_value.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        await client.query("question", "context")

        call_kwargs = mock_anthropic.return_value.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


class TestClaudeClientSkillExecution:
    """Tests for skill execution."""

    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch("src.claude.client.Anthropic") as mock:
            yield mock

    async def test_execute_skill_uses_smart_model(self, mock_anthropic: MagicMock) -> None:
        """Test skill execution uses the smart model."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "# Daily Note\nGenerated content"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        mock_anthropic.return_value.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        result = await client.execute_skill("system prompt", "user prompt")

        assert "Daily Note" in result

        call_kwargs = mock_anthropic.return_value.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"


class TestClaudeClientRetry:
    """Tests for retry logic."""

    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch("src.claude.client.Anthropic") as mock:
            yield mock

    async def test_retry_on_rate_limit(self, mock_anthropic: MagicMock) -> None:
        """Test client retries on rate limit errors."""
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "success"

        mock_response = MagicMock()
        mock_response.content = [mock_text_block]

        # First call fails with rate limit, second succeeds
        mock_anthropic.return_value.messages.create.side_effect = [
            anthropic.RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limited"}},
            ),
            mock_response,
        ]

        client = ClaudeClient(api_key="test-key")

        # Use shorter delays for test by patching asyncio.sleep
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.query("question", "context")

        assert result == "success"
        assert mock_anthropic.return_value.messages.create.call_count == 2

    async def test_max_retries_exceeded(self, mock_anthropic: MagicMock) -> None:
        """Test exception raised after max retries."""
        mock_anthropic.return_value.messages.create.side_effect = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Rate limited"}},
        )

        client = ClaudeClient(api_key="test-key")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Max retries exceeded"):
                await client.query("question", "context")
