"""DuckDB connection management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import duckdb

from .schema import init_database


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

    def execute(self, query: str, params: Optional[list] = None) -> duckdb.DuckDBPyRelation:
        """Execute a query using a per-call cursor for thread safety.

        Note: Callers should consume results (fetchall/fetchone) immediately.
        For explicit cursor lifecycle control, use the cursor() context manager.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query result
        """
        cursor = self.connect().cursor()
        if params:
            return cursor.execute(query, params)
        return cursor.execute(query)

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
