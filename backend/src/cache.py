"""Simple in-memory TTL cache for vault operations."""

import threading
import time
from typing import Any


class TTLCache:
    """Thread-safe TTL cache backed by a plain dict.

    Usage:
        cache = TTLCache(ttl=30)
        cache.set("key", value)
        val = cache.get("key")  # None if expired
        cache.invalidate()       # clear all entries
    """

    def __init__(self, ttl: float = 30.0):
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), value)

    def invalidate(self, key: str | None = None) -> None:
        """Clear a specific key or all entries."""
        with self._lock:
            if key is not None:
                self._store.pop(key, None)
            else:
                self._store.clear()


# Shared cache instances
file_list_cache = TTLCache(ttl=60)
tag_cache = TTLCache(ttl=60)
search_cache = TTLCache(ttl=30)


def invalidate_all() -> None:
    """Invalidate all caches — call on file write/delete."""
    file_list_cache.invalidate()
    tag_cache.invalidate()
    search_cache.invalidate()
