"""Local filesystem storage backend."""

import aiofiles
import aiofiles.os
from pathlib import Path


class LocalFilesystem:
    """Local filesystem storage backend.

    Implements StorageBackend protocol for local file operations.
    """

    def __init__(self, base_path: Path | str) -> None:
        """Initialize local filesystem backend.

        Args:
            base_path: Base directory for all file operations
        """
        self.base_path = Path(base_path).resolve()

    def _resolve_path(self, path: str) -> Path:
        """Resolve relative path to absolute path within base directory.

        Args:
            path: Relative path

        Returns:
            Absolute path within base directory
        """
        resolved = (self.base_path / path).resolve()
        # Security: ensure path is within base directory
        if not str(resolved).startswith(str(self.base_path)):
            raise ValueError(f"Path {path} escapes base directory")
        return resolved

    async def read(self, path: str) -> bytes:
        """Read file contents.

        Args:
            path: Relative path to file

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self._resolve_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def write(self, path: str, content: bytes) -> None:
        """Write content to file.

        Args:
            path: Relative path to file
            content: Content to write

        Creates parent directories if they don't exist.
        """
        full_path = self._resolve_path(path)

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)

    async def delete(self, path: str) -> None:
        """Delete a file.

        Args:
            path: Relative path to file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self._resolve_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        await aiofiles.os.remove(full_path)

    async def list(self, prefix: str = "") -> list[str]:
        """List files with optional prefix filter.

        Args:
            prefix: Path prefix to filter by (e.g., "Daily-Notes/")

        Returns:
            List of relative file paths (files only, not directories)
        """
        search_path = self._resolve_path(prefix) if prefix else self.base_path

        if not search_path.exists():
            return []

        files = []
        for item in search_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(self.base_path)
                files.append(str(rel_path))

        return sorted(files)

    async def exists(self, path: str) -> bool:
        """Check if file exists.

        Args:
            path: Relative path to file

        Returns:
            True if file exists, False otherwise
        """
        full_path = self._resolve_path(path)
        return full_path.exists() and full_path.is_file()
