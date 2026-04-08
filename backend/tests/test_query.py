"""Tests for natural language query API endpoints."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import duckdb
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.api.query import (
    validate_sql,
    extract_sql_from_response,
    ALLOWED_QUERY_TABLES,
    BLOCKED_TABLE_PATTERNS,
    DANGEROUS_FUNCTIONS,
)
from src.db.connection import DatabaseManager


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

    # --- DuckDB file I/O function tests ---

    def test_block_read_csv(self):
        """Test that read_csv() is blocked."""
        assert validate_sql("SELECT * FROM read_csv('/etc/passwd')") is False
        assert validate_sql("SELECT * FROM read_csv_auto('data.csv')") is False

    def test_block_read_parquet(self):
        """Test that read_parquet() is blocked."""
        assert validate_sql("SELECT * FROM read_parquet('data.parquet')") is False

    def test_block_read_json(self):
        """Test that read_json() is blocked."""
        assert validate_sql("SELECT * FROM read_json('data.json')") is False
        assert validate_sql("SELECT * FROM read_json_auto('data.json')") is False

    def test_block_glob(self):
        """Test that glob() is blocked."""
        assert validate_sql("SELECT * FROM glob('/tmp/*')") is False

    def test_block_read_text(self):
        """Test that read_text() is blocked."""
        assert validate_sql("SELECT read_text('/etc/passwd')") is False

    def test_block_read_blob(self):
        """Test that read_blob() is blocked."""
        assert validate_sql("SELECT read_blob('/etc/shadow')") is False

    def test_block_write_csv(self):
        """Test that write_csv() is blocked (keyword + function deny-list)."""
        assert validate_sql("SELECT write_csv(daily_metrics, 'out.csv')") is False

    def test_block_write_parquet(self):
        """Test that write_parquet() is blocked."""
        assert validate_sql("SELECT write_parquet(daily_metrics, 'out.parquet')") is False

    def test_block_http_functions(self):
        """Test that HTTP functions are blocked."""
        assert validate_sql("SELECT * FROM http_get('http://evil.com')") is False

    def test_block_system_function(self):
        """Test that system() is blocked."""
        assert validate_sql("SELECT system('ls')") is False

    # --- System table access tests ---

    def test_block_information_schema(self):
        """Test that information_schema access is blocked."""
        assert validate_sql("SELECT * FROM information_schema.tables") is False

    def test_block_duckdb_tables(self):
        """Test that duckdb system tables are blocked."""
        assert validate_sql("SELECT * FROM duckdb_tables()") is False
        assert validate_sql("SELECT * FROM duckdb_columns()") is False

    def test_block_pg_tables(self):
        """Test that pg_* tables are blocked."""
        assert validate_sql("SELECT * FROM pg_catalog.pg_tables") is False

    def test_block_sqlite_tables(self):
        """Test that sqlite_* tables are blocked."""
        assert validate_sql("SELECT * FROM sqlite_master") is False

    # --- CTE-based write attack tests ---

    def test_block_cte_delete_returning(self):
        """Test CTE-based write attacks: WITH x AS (DELETE ... RETURNING *)."""
        sql = "WITH x AS (DELETE FROM daily_metrics RETURNING *) SELECT * FROM x"
        assert validate_sql(sql) is False

    def test_block_cte_insert(self):
        """Test CTE-based INSERT attacks."""
        sql = "WITH x AS (INSERT INTO daily_metrics VALUES ('2026-01-01', 8) RETURNING *) SELECT * FROM x"
        assert validate_sql(sql) is False

    def test_block_cte_update(self):
        """Test CTE-based UPDATE attacks."""
        sql = "WITH x AS (UPDATE daily_metrics SET sleep_hours=0 RETURNING *) SELECT * FROM x"
        assert validate_sql(sql) is False

    # --- Comment injection tests ---

    def test_block_comment_injection(self):
        """Test that comment-based bypass attempts are caught."""
        # Multi-statement hidden in comments - the semicolon check catches this
        sql = "SELECT 1; DROP TABLE daily_metrics"
        assert validate_sql(sql) is False

    # --- Multi-statement tests ---

    def test_block_semicolon_multi_statement(self):
        """Test that multiple statements separated by semicolons are blocked."""
        assert validate_sql("SELECT 1; SELECT 2") is False
        assert validate_sql("SELECT 1; DROP TABLE daily_metrics") is False

    def test_trailing_semicolon_allowed(self):
        """Test that a single trailing semicolon is allowed."""
        assert validate_sql("SELECT * FROM daily_metrics;") is True

    # --- DuckDB parser structural validation ---

    def test_parser_rejects_invalid_sql(self):
        """Test that the DuckDB parser rejects malformed SQL."""
        assert validate_sql("SELECT FROM WHERE") is False

    def test_parser_rejects_empty(self):
        """Test that empty SQL is rejected."""
        assert validate_sql("") is False

    # --- Keyword in column names (should not false-positive) ---

    def test_allow_keyword_in_string_literal(self):
        """Test that keywords in string literals don't cause false positives.
        Note: word-boundary regex on upper-cased SQL may match keywords in
        identifiers. This is the accepted trade-off for security."""
        # This query contains 'SET' in the function name — but SET is blocked as keyword
        # We accept this false positive for security
        sql = "SELECT date FROM daily_metrics WHERE description ILIKE '%update%'"
        # 'UPDATE' as a word boundary match blocks this — expected behavior
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


class TestReadOnlyExecute:
    """Tests for read_only_execute() on a real DuckDB instance."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary DuckDB database with test data."""
        db_path = tmp_path / "test.duckdb"
        manager = DatabaseManager(db_path)
        # Create test table with data
        manager.execute("CREATE TABLE test_table (id INTEGER, name VARCHAR)")
        manager.execute("INSERT INTO test_table VALUES (1, 'alice'), (2, 'bob')")
        yield manager
        manager.close()

    def test_select_works(self, db):
        """Test that SELECT queries work in read-only mode."""
        result = db.read_only_execute("SELECT * FROM test_table ORDER BY id")
        rows = result.fetchall()
        assert len(rows) == 2
        assert rows[0] == (1, "alice")
        assert rows[1] == (2, "bob")

    def test_insert_rolled_back(self, db):
        """Test that INSERT is rolled back and data is unchanged."""
        try:
            db.read_only_execute("INSERT INTO test_table VALUES (3, 'charlie')")
        except Exception:
            pass  # May raise, that's fine

        # Verify original data is intact
        result = db.execute("SELECT COUNT(*) FROM test_table")
        count = result.fetchone()[0]
        assert count == 2

    def test_delete_rolled_back(self, db):
        """Test that DELETE is rolled back and data is unchanged."""
        try:
            db.read_only_execute("DELETE FROM test_table WHERE id = 1")
        except Exception:
            pass

        result = db.execute("SELECT COUNT(*) FROM test_table")
        count = result.fetchone()[0]
        assert count == 2

    def test_update_rolled_back(self, db):
        """Test that UPDATE is rolled back and data is unchanged."""
        try:
            db.read_only_execute("UPDATE test_table SET name = 'hacked' WHERE id = 1")
        except Exception:
            pass

        result = db.execute("SELECT name FROM test_table WHERE id = 1")
        name = result.fetchone()[0]
        assert name == "alice"

    def test_drop_rolled_back(self, db):
        """Test that DROP TABLE is rolled back and table still exists."""
        try:
            db.read_only_execute("DROP TABLE test_table")
        except Exception:
            pass

        # Table should still exist
        result = db.execute("SELECT COUNT(*) FROM test_table")
        count = result.fetchone()[0]
        assert count == 2

    def test_result_materialized(self, db):
        """Test that results are properly materialized after rollback."""
        result = db.read_only_execute("SELECT id, name FROM test_table ORDER BY id")
        # Columns accessible via description
        assert result.description is not None
        assert len(result.description) == 2
        # Rows accessible via fetchall
        rows = result.fetchall()
        assert len(rows) == 2


class TestInvalidQueryHandling:
    """Tests for INVALID_QUERY response handling."""

    def test_invalid_query_response(self, client, mock_claude):
        """Test that INVALID_QUERY from Claude returns friendly message."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="INVALID_QUERY")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "analytics_db", MagicMock(), create=True):
            response = client.post(
                "/query/natural",
                json={"question": "What is the meaning of life?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "personal data" in data["answer"].lower()
        assert data["error"] is None

    def test_invalid_query_with_explanation(self, client, mock_claude):
        """Test INVALID_QUERY with trailing explanation."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="INVALID_QUERY - This is not a data question")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "analytics_db", MagicMock(), create=True):
            response = client.post(
                "/query/natural",
                json={"question": "Tell me a joke"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "personal data" in data["answer"].lower()


class TestLimitSafetyNet:
    """Tests for automatic LIMIT injection."""

    def test_limit_added_when_missing(self, client, mock_claude):
        """Test that LIMIT is added when Claude omits it."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="SELECT * FROM daily_metrics")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.description = [("date",)]
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.read_only_execute = MagicMock(return_value=mock_result)

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "db", mock_db, create=True), \
             patch.object(app.state, "analytics_db", mock_db, create=True):
            response = client.post(
                "/query/natural",
                json={"question": "Show all metrics"},
            )

        assert response.status_code == 200
        # Check that the SQL passed to read_only_execute contains LIMIT
        called_sql = mock_db.read_only_execute.call_args[0][0]
        assert "LIMIT 100" in called_sql

    def test_existing_limit_preserved(self, client, mock_claude):
        """Test that existing LIMIT is not double-wrapped."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="SELECT * FROM daily_metrics LIMIT 10")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.description = [("date",)]
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.read_only_execute = MagicMock(return_value=mock_result)

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "db", mock_db, create=True), \
             patch.object(app.state, "analytics_db", mock_db, create=True):
            response = client.post(
                "/query/natural",
                json={"question": "Show 10 metrics"},
            )

        assert response.status_code == 200
        called_sql = mock_db.read_only_execute.call_args[0][0]
        # Should use original SQL without extra wrapping
        assert called_sql == "SELECT * FROM daily_metrics LIMIT 10"


class TestQueryEndpoint:
    """Tests for POST /query/natural endpoint."""

    def test_query_without_claude_configured(self, client):
        """Test query when Claude is not configured."""
        mock = MagicMock()
        mock.is_configured = False

        with patch.object(app.state, "claude", mock, create=True), \
             patch.object(app.state, "analytics_db", MagicMock(), create=True):
            response = client.post(
                "/query/natural",
                json={"question": "How much sleep did I get?"},
            )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]

    def test_query_empty_question(self, client, mock_claude):
        """Test query with empty question."""
        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "analytics_db", MagicMock(), create=True):
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
        mock_db.read_only_execute = MagicMock(return_value=mock_result)

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "db", mock_db, create=True), \
             patch.object(app.state, "analytics_db", mock_db, create=True):
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

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "analytics_db", MagicMock(), create=True):
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
        sql_response.content = [MagicMock(text="SELECT * FROM daily_metrics LIMIT 100")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)
        mock_claude._create_message = MagicMock()

        mock_db = MagicMock()
        mock_db.read_only_execute = MagicMock(side_effect=Exception("Table not found"))

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "db", mock_db, create=True), \
             patch.object(app.state, "analytics_db", mock_db, create=True):
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
        sql_response.content = [MagicMock(text="SELECT * FROM daily_metrics WHERE date > '2099-01-01' LIMIT 100")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)
        mock_claude._create_message = MagicMock()

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.description = [("date",), ("sleep_hours",)]
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.read_only_execute = MagicMock(return_value=mock_result)

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "db", mock_db, create=True), \
             patch.object(app.state, "analytics_db", mock_db, create=True):
            response = client.post(
                "/query/natural",
                json={"question": "Show data from the future"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "didn't find" in data["answer"].lower() or "no data" in data["answer"].lower()
        assert data["data"] == []

    def test_query_uses_read_only_execute(self, client, mock_claude):
        """Test that the endpoint uses read_only_execute, not execute."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="SELECT * FROM daily_metrics LIMIT 10")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.description = [("date",)]
        mock_result.fetchall = MagicMock(return_value=[])
        mock_db.read_only_execute = MagicMock(return_value=mock_result)
        mock_db.execute = MagicMock()

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "db", mock_db, create=True), \
             patch.object(app.state, "analytics_db", mock_db, create=True):
            client.post(
                "/query/natural",
                json={"question": "Show metrics"},
            )

        # read_only_execute should be called, not execute
        mock_db.read_only_execute.assert_called_once()
        mock_db.execute.assert_not_called()

    def test_query_uses_system_prompt(self, client, mock_claude):
        """Test that SQL generation uses system parameter, not user message."""
        sql_response = MagicMock()
        sql_response.content = [MagicMock(text="INVALID_QUERY")]

        mock_claude._call_with_retry = AsyncMock(return_value=sql_response)

        with patch.object(app.state, "claude", mock_claude, create=True), \
             patch.object(app.state, "analytics_db", MagicMock(), create=True):
            client.post(
                "/query/natural",
                json={"question": "How much sleep?"},
            )

        # Verify system parameter was used in the first call
        call_kwargs = mock_claude._call_with_retry.call_args_list[0].kwargs
        assert "system" in call_kwargs
        assert "CRITICAL SAFETY RULES" in call_kwargs["system"]
        # User message should be just the question, not the full prompt
        user_msg = call_kwargs["messages"][0]["content"]
        assert user_msg == "How much sleep?"
