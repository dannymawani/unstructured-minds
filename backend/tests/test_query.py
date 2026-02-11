"""Tests for natural language query API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.query import validate_sql, extract_sql_from_response


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_claude():
    """Create mock Claude client."""
    mock = MagicMock()
    mock.is_configured = True
    mock.model_fast = "claude-haiku-4-5-20251001"
    return mock


class TestSQLValidation:
    """Tests for SQL validation function."""

    def test_valid_select_query(self):
        """Test that SELECT queries are allowed."""
        assert validate_sql("SELECT * FROM daily_metrics") is True
        assert validate_sql("SELECT date, sleep_hours FROM daily_metrics WHERE date > '2026-01-01'") is True

    def test_valid_with_cte(self):
        """Test that CTEs are allowed."""
        sql = "WITH recent AS (SELECT * FROM daily_metrics) SELECT * FROM recent"
        assert validate_sql(sql) is True

    def test_invalid_insert(self):
        """Test that INSERT is blocked."""
        assert validate_sql("INSERT INTO daily_metrics VALUES (1, 2, 3)") is False

    def test_invalid_update(self):
        """Test that UPDATE is blocked."""
        assert validate_sql("UPDATE daily_metrics SET sleep_hours = 10") is False

    def test_invalid_delete(self):
        """Test that DELETE is blocked."""
        assert validate_sql("DELETE FROM daily_metrics") is False

    def test_invalid_drop(self):
        """Test that DROP is blocked."""
        assert validate_sql("DROP TABLE daily_metrics") is False

    def test_invalid_truncate(self):
        """Test that TRUNCATE is blocked."""
        assert validate_sql("TRUNCATE daily_metrics") is False

    def test_blocked_in_subquery(self):
        """Test that dangerous keywords in subqueries are blocked."""
        sql = "SELECT * FROM (DELETE FROM daily_metrics)"
        assert validate_sql(sql) is False


class TestSQLExtraction:
    """Tests for SQL extraction from Claude response."""

    def test_extract_from_code_block(self):
        """Test extracting SQL from markdown code block."""
        response = """Here's the SQL query:
```sql
SELECT date, sleep_hours FROM daily_metrics
```
"""
        assert extract_sql_from_response(response) == "SELECT date, sleep_hours FROM daily_metrics"

    def test_extract_without_code_block(self):
        """Test extracting SQL without markdown formatting."""
        response = "SELECT date, sleep_hours FROM daily_metrics;"
        assert extract_sql_from_response(response) == "SELECT date, sleep_hours FROM daily_metrics"

    def test_extract_with_cte(self):
        """Test extracting CTE query."""
        response = "WITH recent AS (SELECT * FROM daily_metrics) SELECT * FROM recent"
        assert extract_sql_from_response(response) == response

    def test_extract_multiline(self):
        """Test extracting multiline SQL."""
        response = """```sql
SELECT
    date,
    sleep_hours
FROM daily_metrics
WHERE date > '2026-01-01'
```"""
        result = extract_sql_from_response(response)
        assert "SELECT" in result
        assert "FROM daily_metrics" in result


class TestQueryEndpoint:
    """Tests for POST /query/natural endpoint."""

    def test_query_without_claude_configured(self, client):
        """Test query when Claude is not configured."""
        mock = MagicMock()
        mock.is_configured = False

        with patch.object(app.state, "claude", mock):
            response = client.post(
                "/query/natural",
                json={"question": "How much sleep did I get?"},
            )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]

    def test_query_empty_question(self, client, mock_claude):
        """Test query with empty question."""
        with patch.object(app.state, "claude", mock_claude):
            response = client.post(
                "/query/natural",
                json={"question": "   "},
            )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"]

    def test_query_success(self, client, mock_claude):
        """Test successful query execution."""
        # Mock the SQL generation response
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="SELECT date, sleep_hours FROM daily_metrics LIMIT 10")]

        # Mock the formatting response
        format_response = MagicMock()
        format_response.content = [MagicMock(text="You slept an average of 7 hours.")]

        mock_claude._call_with_retry = AsyncMock(side_effect=[sql_response, format_response])
        mock_claude._create_message = MagicMock()

        # Mock database
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.description = [("date",), ("sleep_hours",)]
        mock_result.fetchall = MagicMock(return_value=[
            ("2026-01-01", 7.5),
            ("2026-01-02", 8.0),
        ])
        mock_db.execute = MagicMock(return_value=mock_result)

        with patch.object(app.state, "claude", mock_claude), \
             patch.object(app.state, "db", mock_db), \
             patch.object(app.state, "analytics_db", mock_db):
            response = client.post(
                "/query/natural",
                json={"question": "How much sleep did I get?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "You slept an average of 7 hours."
        assert data["sql"] is not None
        assert data["data"] is not None
        assert data["columns"] == ["date", "sleep_hours"]
        assert data["row_count"] == 2

    def test_query_unsafe_sql_rejected(self, client, mock_claude):
        """Test that unsafe SQL is rejected."""
        # Mock Claude returning dangerous SQL
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="DROP TABLE daily_metrics")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)
        mock_claude._create_message = MagicMock()

        with patch.object(app.state, "claude", mock_claude):
            response = client.post(
                "/query/natural",
                json={"question": "Delete all my data"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "read-only" in data["answer"].lower()
        assert data["error"] is not None

    def test_query_database_error(self, client, mock_claude):
        """Test handling of database errors."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="SELECT * FROM nonexistent_table")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)
        mock_claude._create_message = MagicMock()

        mock_db = MagicMock()
        mock_db.execute = MagicMock(side_effect=Exception("Table not found"))

        with patch.object(app.state, "claude", mock_claude), \
             patch.object(app.state, "db", mock_db):
            response = client.post(
                "/query/natural",
                json={"question": "Show nonexistent data"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "trouble" in data["answer"].lower() or "error" in data["answer"].lower()
        assert data["error"] is not None

    def test_query_no_results(self, client, mock_claude):
        """Test query with no results."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="SELECT * FROM daily_metrics WHERE date > '2099-01-01'")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)
        mock_claude._create_message = MagicMock()

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.description = [("date",), ("sleep_hours",)]
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.execute = MagicMock(return_value=mock_result)

        with patch.object(app.state, "claude", mock_claude), \
             patch.object(app.state, "db", mock_db):
            response = client.post(
                "/query/natural",
                json={"question": "Show data from the future"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "didn't find" in data["answer"].lower() or "no data" in data["answer"].lower()
        assert data["data"] == []
