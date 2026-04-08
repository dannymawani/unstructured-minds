"""Storage backend protocol definition."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends.

    All storage implementations must implement these methods.
    """

    async def read(self, path: str) -> bytes:
        """Read file contents.

        Args:
            path: Relative path to file

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    async def write(self, path: str, content: bytes) -> None:
        """Write content to file.

        Args:
            path: Relative path to file
            content: Content to write

        Creates parent directories if they don't exist.
        """
        ...

    async def delete(self, path: str) -> None:
        """Delete a file.

        Args:
            path: Relative path to file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    async def list(self, prefix: str = "") -> list[str]:
        """List files with optional prefix filter.

        Args:
            prefix: Path prefix to filter by (e.g., "Daily-Notes/")

        Returns:
            List of relative file paths
        """
        ...

    async def rename(self, old_path: str, new_path: str) -> None:
        """Rename/move a file.

        Args:
            old_path: Current relative path
            new_path: New relative path

        Raises:
            FileNotFoundError: If source file doesn't exist
            FileExistsError: If destination file already exists
        """
        ...

    async def exists(self, path: str) -> bool:
        """Check if file exists.

        Args:
            path: Relative path to file

        Returns:
            True if file exists, False otherwise
        """
        ...
