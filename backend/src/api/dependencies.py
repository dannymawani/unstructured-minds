"""Shared FastAPI dependencies for database and storage access."""

from fastapi import Request

from ..storage import StorageBackend
from ..storage.datastore import DataStore


def get_db(request: Request):
    """Get the primary database (Postgres in hybrid/postgres mode, DuckDB in local mode)."""
    return request.app.state.db


def get_analytics_db(request: Request):
    """Get the analytics database (DuckDB cache in hybrid mode, same as db otherwise)."""
    return request.app.state.analytics_db


def get_storage(request: Request) -> StorageBackend:
    """Get the vault storage backend."""
    return request.app.state.storage


def get_datastore(request: Request) -> DataStore:
    """Get the data storage (JSON config files)."""
    return request.app.state.datastore
