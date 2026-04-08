"""Postgres connection management via psycopg3 connection pool."""

from collections.abc import Callable
from contextlib import contextmanager

import psycopg
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool, NullConnectionPool

from ..logging_config import get_logger

logger = get_logger(__name__)


class _PgResult:
    """Wrapper that mimics the DuckDB result interface (description, fetchall, fetchone)."""

    def __init__(self, cursor: psycopg.Cursor) -> None:
        self._cursor = cursor
        self.description = cursor.description or []

    def fetchall(self) -> list[tuple]:
        return self._cursor.fetchall()

    def fetchone(self) -> tuple | None:
        return self._cursor.fetchone()


def _convert_placeholders(query: str) -> str:
    """Convert DuckDB-style ? placeholders to psycopg %s placeholders.

    Skips question marks inside single-quoted strings.
    """
    result = []
    in_string = False
    for char in query:
        if char == "'" and not in_string:
            in_string = True
            result.append(char)
        elif char == "'" and in_string:
            in_string = False
            result.append(char)
        elif char == "?" and not in_string:
            result.append("%s")
        else:
            result.append(char)
    return "".join(result)


class PostgresManager:
    """Manages Postgres connections via a connection pool.

    Implements the same interface as DatabaseManager so API code can
    use either backend interchangeably.
    """

    def __init__(
        self,
        connection_string: str,
        pool_min: int = 2,
        pool_max: int = 10,
        token_callback: Callable[[], str] | None = None,
    ) -> None:
        self._conninfo = connection_string
        self._pool: ConnectionPool | NullConnectionPool | None = None
        self._pool_min = pool_min
        self._pool_max = pool_max
        self._token_callback = token_callback

    def _make_conninfo(self) -> str:
        """Build connection string, injecting a fresh token as password if using token auth."""
        if self._token_callback:
            token = self._token_callback()
            return f"{self._conninfo} password={token}"
        return self._conninfo

    def connect(self) -> None:
        """Open the connection pool."""
        if self._pool is not None:
            return

        conninfo = self._make_conninfo()
        pool_kwargs = {
            "kwargs": {
                "row_factory": tuple_row,
                # Disable prepared statements so the pool works with
                # transaction-mode poolers (PgBouncer / Supavisor).
                "prepare_threshold": None,
            },
        }

        if self._token_callback:
            # Token auth: use NullConnectionPool so each checkout gets a fresh
            # connection with a current token. Acceptable for low-concurrency
            # workloads (~10 users). Each connection adds ~10ms overhead.
            self._pool = NullConnectionPool(
                conninfo,
                max_size=self._pool_max,
                **pool_kwargs,
            )
            logger.info("postgres_pool_opened", mode="token_auth", pool_type="null")
        else:
            self._pool = ConnectionPool(
                conninfo,
                min_size=self._pool_min,
                max_size=self._pool_max,
                **pool_kwargs,
            )
            logger.info("postgres_pool_opened", mode="password", pool_type="connection")

    def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            self._pool.close()
            self._pool = None
            logger.info("postgres_pool_closed")

    @contextmanager
    def cursor(self):
        """Get a cursor from the pool. Auto-commits on success, rolls back on error."""
        if self._pool is None:
            raise RuntimeError("PostgresManager not connected. Call connect() first.")
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                yield cur

    def execute(self, query: str, params: list | None = None) -> _PgResult:
        """Execute a query and return a result wrapper.

        Auto-converts ? placeholders to %s for Postgres.
        Callers should consume results (fetchall/fetchone) immediately.
        """
        if self._pool is None:
            raise RuntimeError("PostgresManager not connected. Call connect() first.")

        pg_query = _convert_placeholders(query)

        conn = self._pool.getconn()
        try:
            cur = conn.cursor()
            if params:
                cur.execute(pg_query, params)
            else:
                cur.execute(pg_query)
            conn.commit()
            return _PgResult(cur)
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def __enter__(self) -> "PostgresManager":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
