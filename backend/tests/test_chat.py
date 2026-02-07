"""Tests for chat API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_claude():
    """Create mock Claude client."""
    mock = MagicMock()
    mock.is_configured = True
    mock.query = AsyncMock(return_value="This is a test response.")
    return mock


class TestChatEndpoint:
    """Tests for POST /chat endpoint."""

    def test_chat_returns_response(self, client, mock_claude):
        """Test successful chat response."""
        with patch.object(app.state, "claude", mock_claude):
            response = client.post(
                "/chat",
                json={"message": "What is my exercise data?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"]["role"] == "assistant"
        assert data["message"]["content"] == "This is a test response."
        assert "context_used" in data

    def test_chat_without_claude_configured(self, client):
        """Test chat when Claude is not configured."""
        mock = MagicMock()
        mock.is_configured = False

        with patch.object(app.state, "claude", mock):
            response = client.post(
                "/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]

    def test_chat_with_custom_context(self, client, mock_claude):
        """Test chat with user-provided context."""
        with patch.object(app.state, "claude", mock_claude):
            response = client.post(
                "/chat",
                json={
                    "message": "Summarize this",
                    "context": "Custom context data",
                },
            )

        assert response.status_code == 200
        mock_claude.query.assert_called_once()
        # Verify custom context was passed
        call_args = mock_claude.query.call_args
        assert call_args[0][1] == "Custom context data"

    def test_chat_query_failure(self, client):
        """Test chat when query fails."""
        mock = MagicMock()
        mock.is_configured = True
        mock.query = AsyncMock(side_effect=Exception("API error"))

        with patch.object(app.state, "claude", mock):
            response = client.post(
                "/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == 500
        assert "Chat failed" in response.json()["detail"]

    def test_chat_empty_message(self, client, mock_claude):
        """Test chat with empty message returns validation error."""
        with patch.object(app.state, "claude", mock_claude):
            response = client.post(
                "/chat",
                json={"message": ""},
            )

        # min_length=1 on ChatRequest.message rejects empty strings
        assert response.status_code == 422

    def test_chat_gathers_context_from_db(self, client, mock_claude):
        """Test that chat gathers context from database."""
        with patch.object(app.state, "claude", mock_claude):
            response = client.post(
                "/chat",
                json={"message": "What exercise did I do?"},
            )

        assert response.status_code == 200
        # Query should have been called with some context
        mock_claude.query.assert_called_once()
