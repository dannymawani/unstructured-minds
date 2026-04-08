"""Database Layer — DuckDB + Postgres."""

from .connection import DatabaseManager
from .postgres import PostgresManager
from .postgres_schema import init_postgres_schema
from .schema import get_table_names, init_database
from .sql_compat import get_dialect, upsert

__all__ = [
    "DatabaseManager",
    "init_database",
    "get_table_names",
    "PostgresManager",
    "init_postgres_schema",
    "upsert",
    "get_dialect",
]
