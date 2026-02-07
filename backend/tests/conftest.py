"""Global test configuration and fixtures."""

import pytest

from src.cache import invalidate_all


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches before and after each test to prevent leakage."""
    invalidate_all()
    yield
    invalidate_all()
