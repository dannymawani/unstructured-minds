"""Storage Abstraction Layer.

Provides pluggable storage backends for file operations.
"""

from pathlib import Path

from .base import StorageBackend
from .local import LocalFilesystem
from .postgres import PostgresStorage

__all__ = ["StorageBackend", "LocalFilesystem", "PostgresStorage", "get_storage_backend"]


def get_storage_backend(backend_type: str = "local", **kwargs) -> StorageBackend:
    """Factory function to get storage backend.

    Args:
        backend_type: Type of backend ("local", "postgres")
        **kwargs: Backend-specific configuration
            For "local": base_path (Path)
            For "postgres": pool (psycopg_pool.AsyncConnectionPool), user_id (str)

    Returns:
        StorageBackend instance

    Raises:
        ValueError: If backend_type is not supported
    """
    if backend_type == "local":
        base_path = kwargs.get("base_path", Path.cwd())
        return LocalFilesystem(base_path=base_path)
    elif backend_type == "postgres":
        return PostgresStorage(pg=kwargs["pg"], user_id=kwargs["user_id"])
    else:
        raise ValueError(f"Unsupported storage backend: {backend_type}")
