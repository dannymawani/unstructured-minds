"""Shared FastAPI dependencies for database and storage access."""

import uuid

from fastapi import Request

from ..config import settings
from ..middleware.clerk_auth import verify_clerk_token
from ..storage import StorageBackend
from ..storage.datastore import DataStore

# Deterministic namespace for mapping Clerk IDs to UUIDs.
# Uses the standard NAMESPACE_URL so the same Clerk sub always yields the same UUID.
CLERK_NAMESPACE = uuid.UUID("6ba7b811-6ba5-11d1-80b6-00c04fd430c8")


def get_db(request: Request):
    """Get the primary database (Postgres in hybrid/postgres mode, DuckDB in local mode)."""
    return request.app.state.db


def get_analytics_db(request: Request):
    """Get the analytics database (DuckDB cache in hybrid mode, same as db otherwise)."""
    return request.app.state.analytics_db


def get_storage(request: Request) -> StorageBackend:
    """Get the vault storage backend (user-scoped in cloud mode)."""
    if settings.is_cloud_mode:
        from ..storage.postgres import PostgresStorage

        user_id = get_user_id(request)
        return PostgresStorage(request.app.state.db, user_id)
    return request.app.state.storage


def get_datastore(request: Request) -> DataStore:
    """Get the data storage (user-scoped in cloud mode)."""
    if settings.is_cloud_mode:
        from ..storage.postgres import PostgresStorage

        user_id = get_user_id(request)
        data_storage = PostgresStorage(request.app.state.db, user_id, "_data")
        return DataStore(data_storage)
    return request.app.state.datastore


def get_user_id(request: Request) -> str:
    """Return the authenticated user ID as a UUID string.

    When Clerk auth is configured, maps the Clerk sub claim to a
    deterministic UUID via uuid5 so it fits Postgres UUID columns.
    When auth is disabled, returns DEFAULT_USER_ID for local/dev mode.
    """
    if not settings.auth_enabled:
        return settings.default_user_id
    payload = verify_clerk_token(request)
    return str(uuid.uuid5(CLERK_NAMESPACE, payload["sub"]))
