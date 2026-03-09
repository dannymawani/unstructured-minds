"""DuckDB connection management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import duckdb

from .schema import init_database


class _MaterializedResult:
    """Holds materialized query results after cursor is closed."""

    def __init__(self, description, rows):
        self.description = description
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class DatabaseManager:
    """Manages DuckDB database connections."""

    def __init__(self, db_path: Path | str) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection.

        Returns:
            DuckDB connection
        """
        if self._conn is None:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = init_database(self.db_path)
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @contextmanager
    def cursor(self):
        """Get a cursor that auto-closes when done.

        Usage:
            with db.cursor() as cur:
                cur.execute("SELECT ...").fetchall()
        """
        cur = self.connect().cursor()
        try:
            yield cur
        finally:
            cur.close()

    def read_only_execute(self, query: str) -> _MaterializedResult:
        """Execute a query in read-only mode, preventing any writes.

        Uses BEGIN TRANSACTION / ROLLBACK to ensure any write attempts
        are discarded. This is a defense-in-depth measure for
        AI-generated SQL.

        Args:
            query: SQL query (should be SELECT/WITH only)

        Returns:
            Query result

        Raises:
            duckdb.Error: If the query is invalid or attempts writes
        """
        cursor = self.connect().cursor()
        try:
            cursor.execute("BEGIN TRANSACTION")
            result = cursor.execute(query)
            columns = result.description
            rows = result.fetchall()
            return _MaterializedResult(columns, rows)
        finally:
            try:
                cursor.execute("ROLLBACK")
            except Exception:
                pass
            cursor.close()

    def execute(self, query: str, params: Optional[list] = None) -> _MaterializedResult:
        """Execute a query using a per-call cursor for thread safety.

        Results are materialized immediately and the cursor is closed,
        preventing cursor leaks in long-running processes.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Materialized query result supporting fetchall()/fetchone()
        """
        cursor = self.connect().cursor()
        try:
            if params:
                result = cursor.execute(query, params)
            else:
                result = cursor.execute(query)
            desc = result.description
            rows = result.fetchall()
            return _MaterializedResult(desc, rows)
        finally:
            cursor.close()

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
