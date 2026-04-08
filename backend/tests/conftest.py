"""Global test configuration and fixtures."""

from unittest.mock import patch

import pytest

from src.cache import invalidate_all
from src.config import LOCAL_USER_ID


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before and after each test to prevent leakage."""
    invalidate_all()
    yield
    invalidate_all()


@pytest.fixture(autouse=True)
def disable_auth():
    """Bypass Clerk auth in tests by forcing local mode in dependencies.

    The dev .env has CLERK_SECRET_KEY/CLERK_DOMAIN/DATABASE_URL set,
    making the real settings.auth_enabled and settings.is_cloud_mode True.
    Test fixtures mock src.main.settings (for app startup) but not
    src.api.dependencies.settings, so get_storage()/get_datastore() use
    the real settings, hit the cloud-mode branch, call get_user_id()
    directly (not via DI), and fail with 401.

    Patching dependencies.settings ensures:
    - get_storage/get_datastore take the local branch (is_cloud_mode=False)
    - get_user_id returns LOCAL_USER_ID without JWT verification
    """
    from src.api.dependencies import get_user_id
    from src.main import app

    # DI override — covers endpoints using Depends(get_user_id) directly
    app.dependency_overrides[get_user_id] = lambda: LOCAL_USER_ID

    # Patch the settings object that dependencies.py actually uses
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.auth_enabled = False
        mock_settings.is_cloud_mode = False
        yield

    app.dependency_overrides.pop(get_user_id, None)
