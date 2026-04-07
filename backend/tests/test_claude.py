"""Tests for LLM client (provider-agnostic via LiteLLM)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import litellm

from src.llm.client import LLMClient


class TestLLMClientInit:
    """Tests for LLMClient initialization."""

    def test_client_init_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test client initializes with provided API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        client = LLMClient(api_key="sk-ant-test-key")
        assert client.is_configured is True
        assert client.provider == "anthropic"

    def test_client_detects_anthropic_from_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test client auto-detects Anthropic from key prefix."""
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        client = LLMClient(api_key="sk-ant-test")
        assert client.provider == "anthropic"

    def test_client_detects_openai_from_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test client auto-detects OpenAI from key prefix."""
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(api_key="sk-proj-test")
        assert client.provider == "openai"

    def test_explicit_provider(self) -> None:
        """Test explicit provider overrides detection."""
        client = LLMClient(provider="ollama")
        assert client.provider == "ollama"
        assert client.is_configured is True  # Ollama doesn't need API key

    def test_is_configured_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test is_configured returns False without API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = LLMClient(provider="anthropic")
        assert client.is_configured is False

    def test_model_defaults_per_provider(self) -> None:
        """Test correct default models per provider."""
        client = LLMClient(provider="openai", api_key="sk-test")
        assert "gpt-4o-mini" in client.model_fast
        assert "gpt-4o" in client.model_smart


class TestLLMClientExtraction:
    """Tests for extraction functionality."""

    @pytest.fixture
    def mock_litellm(self):
        """Mock litellm.acompletion."""
        with patch("src.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            yield mock

    def _make_tool_response(self, tool_name, arguments):
        """Create a mock LiteLLM response with a tool call."""
        tc = MagicMock()
        tc.function.name = tool_name
        tc.function.arguments = arguments

        msg = MagicMock()
        msg.content = None
        msg.tool_calls = [tc]

        choice = MagicMock()
        choice.message = msg

        resp = MagicMock()
        resp.choices = [choice]
        return resp

    def _make_text_response(self, text):
        """Create a mock LiteLLM response with text."""
        msg = MagicMock()
        msg.content = text
        msg.tool_calls = None

        choice = MagicMock()
        choice.message = msg

        resp = MagicMock()
        resp.choices = [choice]
        return resp

    async def test_extraction_returns_json(self, mock_litellm) -> None:
        """Test extraction parses tool use response."""
        mock_litellm.return_value = self._make_tool_response(
            "extract_data",
            '{"exercise_log": [{"name": "squat", "weight_kg": 100}]}',
        )

        client = LLMClient(api_key="sk-ant-test")
        result = await client.extract("# Test content", {"type": "object"})

        assert "exercise_log" in result
        assert result["exercise_log"][0]["name"] == "squat"

    async def test_extraction_calls_with_tool(self, mock_litellm) -> None:
        """Test extraction passes tool to API."""
        mock_litellm.return_value = self._make_tool_response("extract_data", "{}")

        client = LLMClient(api_key="sk-ant-test")
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        await client.extract("content", schema)

        call_kwargs = mock_litellm.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"][0]["function"]["name"] == "extract_data"


class TestLLMClientQuery:
    """Tests for query functionality."""

    @pytest.fixture
    def mock_litellm(self):
        with patch("src.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            yield mock

    async def test_query_returns_text(self, mock_litellm) -> None:
        """Test query returns response text."""
        msg = MagicMock()
        msg.content = "You did 5 workouts this week."
        msg.tool_calls = None
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        mock_litellm.return_value = resp

        client = LLMClient(api_key="sk-ant-test")
        result = await client.query("How many workouts?", "workout data here")

        assert result == "You did 5 workouts this week."

    async def test_query_uses_fast_model(self, mock_litellm) -> None:
        """Test query uses the fast model."""
        msg = MagicMock()
        msg.content = "answer"
        msg.tool_calls = None
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        mock_litellm.return_value = resp

        client = LLMClient(api_key="sk-ant-test")
        await client.query("question", "context")

        call_kwargs = mock_litellm.call_args[1]
        assert "haiku" in call_kwargs["model"]


class TestLLMClientSkillExecution:
    """Tests for skill execution."""

    @pytest.fixture
    def mock_litellm(self):
        with patch("src.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            yield mock

    async def test_execute_skill_uses_smart_model(self, mock_litellm) -> None:
        """Test skill execution uses the smart model."""
        msg = MagicMock()
        msg.content = "# Daily Note\nGenerated content"
        msg.tool_calls = None
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        mock_litellm.return_value = resp

        client = LLMClient(api_key="sk-ant-test")
        result = await client.execute_skill("system prompt", "user prompt")

        assert "Daily Note" in result
        call_kwargs = mock_litellm.call_args[1]
        assert "sonnet" in call_kwargs["model"]


class TestLLMClientRetry:
    """Tests for retry logic."""

    @pytest.fixture
    def mock_litellm(self):
        with patch("src.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock:
            yield mock

    async def test_retry_on_rate_limit(self, mock_litellm) -> None:
        """Test client retries on rate limit errors."""
        msg = MagicMock()
        msg.content = "success"
        msg.tool_calls = None
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]

        mock_litellm.side_effect = [
            litellm.RateLimitError(
                message="Rate limited",
                model="test",
                llm_provider="anthropic",
            ),
            resp,
        ]

        client = LLMClient(api_key="sk-ant-test")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.query("question", "context")

        assert result == "success"
        assert mock_litellm.call_count == 2

    async def test_max_retries_exceeded(self, mock_litellm) -> None:
        """Test exception raised after max retries."""
        mock_litellm.side_effect = litellm.RateLimitError(
            message="Rate limited",
            model="test",
            llm_provider="anthropic",
        )

        client = LLMClient(api_key="sk-ant-test")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Max retries exceeded"):
                await client.query("question", "context")
