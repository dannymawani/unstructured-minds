"""DataStore: JSON-aware wrapper around StorageBackend for config/data files."""

import json
from typing import Any

from .base import StorageBackend


class DataStore:
    """High-level data access layer on top of a StorageBackend.

    Provides JSON read/write helpers and maps data/ file paths to storage operations.
    Works identically whether the underlying backend is local filesystem or Postgres.
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

    @property
    def storage(self) -> StorageBackend:
        """Access the underlying StorageBackend."""
        return self._storage

    async def read_json(self, path: str) -> dict[str, Any] | None:
        """Read and parse a JSON file.

        Args:
            path: Relative path to JSON file (e.g., "settings.json")

        Returns:
            Parsed dict, or None if file doesn't exist
        """
        try:
            data = await self._storage.read(path)
            return json.loads(data.decode("utf-8"))
        except FileNotFoundError:
            return None

    async def write_json(self, path: str, data: dict[str, Any]) -> None:
        """Serialize and write a dict as JSON.

        Args:
            path: Relative path to JSON file
            data: Dict to serialize
        """
        content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        await self._storage.write(path, content)

    async def read_bytes(self, path: str) -> bytes | None:
        """Read raw bytes from a file.

        Returns None instead of raising if file doesn't exist.
        """
        try:
            return await self._storage.read(path)
        except FileNotFoundError:
            return None

    async def write_bytes(self, path: str, content: bytes) -> None:
        """Write raw bytes to a file."""
        await self._storage.write(path, content)

    async def delete_file(self, path: str) -> bool:
        """Delete a file. Returns True if deleted, False if it didn't exist."""
        try:
            await self._storage.delete(path)
            return True
        except FileNotFoundError:
            return False

    async def list_files(self, prefix: str = "") -> list[str]:
        """List files with optional prefix filter."""
        return await self._storage.list(prefix)

    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        return await self._storage.exists(path)
