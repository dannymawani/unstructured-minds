"""Global test configuration and fixtures."""

import pytest

from src.cache import invalidate_all
from src.config import settings


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before and after each test to prevent leakage."""
    invalidate_all()
    yield
    invalidate_all()


@pytest.fixture(autouse=True)
def disable_auth():
    """Bypass Clerk auth in tests by overriding the get_user_id dependency.

    backend/.env may contain CLERK_SECRET_KEY / CLERK_DOMAIN, which makes
    settings.auth_enabled True.  Without a valid JWT the dependency would
    raise 401.  Overriding it returns the default user ID for all tests.
    """
    from src.main import app
    from src.api.dependencies import get_user_id

    app.dependency_overrides[get_user_id] = lambda: settings.default_user_id
    yield
    app.dependency_overrides.pop(get_user_id, None)
