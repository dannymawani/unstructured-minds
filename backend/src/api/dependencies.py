"""Shared FastAPI dependencies for database and storage access."""

from fastapi import Request

from ..config import settings
from ..middleware.clerk_auth import verify_clerk_token
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


def get_user_id(request: Request) -> str:
    """Return the authenticated user ID.

    When Clerk auth is configured, verifies the JWT and returns the Clerk
    user ID (sub claim). When auth is disabled, returns DEFAULT_USER_ID
    so local/dev mode works without any auth setup.
    """
    if not settings.auth_enabled:
        return settings.default_user_id
    payload = verify_clerk_token(request)
    return payload["sub"]
