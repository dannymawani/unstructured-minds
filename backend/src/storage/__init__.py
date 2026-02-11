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
        backend_type: Type of backend ("local", "s3")
        **kwargs: Backend-specific configuration
            For "local": base_path (Path)
            For "s3": bucket, endpoint_url, region_name, access_key_id,
                       secret_access_key, prefix

    Returns:
        StorageBackend instance

    Raises:
        ValueError: If backend_type is not supported
    """
    if backend_type == "local":
        base_path = kwargs.get("base_path", Path.cwd())
        return LocalFilesystem(base_path=base_path)
    elif backend_type == "s3":
        from .s3 import S3Storage

        return S3Storage(
            bucket=kwargs["bucket"],
            endpoint_url=kwargs["endpoint_url"],
            region_name=kwargs.get("region_name", "us-east-1"),
            access_key_id=kwargs["access_key_id"],
            secret_access_key=kwargs["secret_access_key"],
            prefix=kwargs.get("prefix", ""),
        )
    else:
        raise ValueError(f"Unsupported storage backend: {backend_type}")
