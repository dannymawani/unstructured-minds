"""Storage Abstraction Layer.

Provides pluggable storage backends for file operations.
"""

from pathlib import Path

from .base import StorageBackend
from .local import LocalFilesystem

__all__ = ["StorageBackend", "LocalFilesystem", "get_storage_backend"]


def get_storage_backend(backend_type: str = "local", **kwargs) -> StorageBackend:
    """Factory function to get storage backend.

    Args:
        backend_type: Type of backend ("local", "azure", "s3")
        **kwargs: Backend-specific configuration

    Returns:
        StorageBackend instance

    Raises:
        ValueError: If backend_type is not supported
    """
    if backend_type == "local":
        base_path = kwargs.get("base_path", Path.cwd())
        return LocalFilesystem(base_path=base_path)
    else:
        raise ValueError(f"Unsupported storage backend: {backend_type}")
