"""Database Layer — DuckDB + Postgres."""

from .connection import DatabaseManager
from .schema import init_database, get_table_names
from .postgres import PostgresManager
from .postgres_schema import init_postgres_schema
from .sql_compat import upsert, get_dialect

__all__ = [
    "DatabaseManager",
    "init_database",
    "get_table_names",
    "PostgresManager",
    "init_postgres_schema",
    "upsert",
    "get_dialect",
]
