"""DuckDB connection management."""

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

    def execute(self, query: str, params: Optional[list] = None) -> duckdb.DuckDBPyRelation:
        """Execute a query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query result
        """
        conn = self.connect()
        if params:
            return conn.execute(query, params)
        return conn.execute(query)

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
