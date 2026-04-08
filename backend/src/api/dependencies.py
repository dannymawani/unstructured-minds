"""Shared FastAPI dependencies for database and storage access."""

import uuid

from fastapi import HTTPException, Request

from ..config import LOCAL_USER_ID, settings
from ..storage import StorageBackend
from ..storage.datastore import DataStore

# Deterministic namespace for mapping Clerk IDs to UUIDs.
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


def _resolve_auth_mode() -> str:
    """Determine the effective auth mode.

    Checks auth_mode setting first. Falls back to cloud mode detection
    for backward compatibility (cloud mode + Clerk keys = clerk auth).
    """
    if settings.auth_mode != "none":
        return settings.auth_mode
    # Backward compat: cloud mode with Clerk implies clerk auth
    if settings.is_cloud_mode and settings.clerk_secret_key:
        return "clerk"
    return "none"


def get_user_id(request: Request) -> str:
    """Return the authenticated user ID.

    Auth modes:
    - none: returns LOCAL_USER_ID (single implicit user)
    - basic: verifies HTTP Basic Auth, returns LOCAL_USER_ID
    - clerk: verifies Clerk JWT, maps sub to deterministic UUID

    Results are cached on request.state so multiple dependencies
    calling this within the same request only verify once.
    """
    cached = getattr(request.state, "_user_id", None)
    if cached is not None:
        return cached

    mode = _resolve_auth_mode()

    if mode == "none":
        uid = LOCAL_USER_ID

    elif mode == "basic":
        from ..middleware.basic_auth import verify_basic_auth
        verify_basic_auth(request)
        uid = LOCAL_USER_ID

    elif mode == "clerk":
        from ..middleware.clerk_auth import verify_clerk_token
        if not settings.clerk_secret_key or not settings.clerk_domain:
            raise HTTPException(
                500,
                "Clerk auth requires CLERK_SECRET_KEY and CLERK_DOMAIN",
            )
        payload = verify_clerk_token(request)
        uid = str(uuid.uuid5(CLERK_NAMESPACE, payload["sub"]))

        # Seed the analytics cache on first login
        cache_mgr = getattr(request.app.state, "analytics_cache_manager", None)
        if cache_mgr and cache_mgr._user_id is None:
            cache_mgr.refresh(user_id=uid)
    else:
        raise HTTPException(500, f"Unknown AUTH_MODE: {mode}")

    request.state._user_id = uid
    return uid
