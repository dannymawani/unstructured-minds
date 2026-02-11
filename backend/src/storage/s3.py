"""S3-compatible storage backend for Supabase Storage."""

import asyncio
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ..logging_config import get_logger

logger = get_logger(__name__)


class S3Storage:
    """S3-compatible storage backend (Supabase Storage).

    Implements StorageBackend protocol using boto3.
    All boto3 calls are wrapped in asyncio.to_thread() since boto3 is synchronous.
    """

    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        region_name: str,
        access_key_id: str,
        secret_access_key: str,
        prefix: str = "",
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
        logger.info(
            "s3_storage_initialized",
            bucket=bucket,
            prefix=self.prefix,
            endpoint=endpoint_url,
        )

    def _full_key(self, path: str) -> str:
        """Build the full S3 key from a relative path."""
        path = path.lstrip("/")
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path

    def _strip_prefix(self, key: str) -> str:
        """Strip the prefix from an S3 key to get a relative path."""
        if self.prefix and key.startswith(f"{self.prefix}/"):
            return key[len(self.prefix) + 1 :]
        return key

    # ------------------------------------------------------------------
    # StorageBackend protocol methods
    # ------------------------------------------------------------------

    async def read(self, path: str) -> bytes:
        """Read file contents from S3."""
        key = self._full_key(path)
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self.bucket, Key=key
            )
            body = await asyncio.to_thread(response["Body"].read)
            return body
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {path}") from e
            raise

    async def write(self, path: str, content: bytes) -> None:
        """Write content to S3."""
        key = self._full_key(path)
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=content,
        )

    async def delete(self, path: str) -> None:
        """Delete a file from S3."""
        key = self._full_key(path)
        # Check existence first (S3 delete is idempotent but protocol requires error)
        if not await self.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self.bucket, Key=key
        )

    async def list(self, prefix: str = "") -> list[str]:
        """List files with optional prefix filter, handling pagination."""
        search_prefix = self._full_key(prefix) if prefix else (self.prefix + "/" if self.prefix else "")

        files: list[str] = []
        continuation_token: str | None = None

        while True:
            kwargs: dict[str, Any] = {
                "Bucket": self.bucket,
                "Prefix": search_prefix,
                "MaxKeys": 1000,
            }
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = await asyncio.to_thread(
                self._client.list_objects_v2, **kwargs
            )

            for obj in response.get("Contents", []):
                key = obj["Key"]
                relative = self._strip_prefix(key)
                if relative:  # skip empty (the prefix itself)
                    files.append(relative)

            if response.get("IsTruncated"):
                continuation_token = response["NextContinuationToken"]
            else:
                break

        return sorted(files)

    async def rename(self, old_path: str, new_path: str) -> None:
        """Rename/move a file (copy + delete, S3 has no native rename)."""
        if not await self.exists(old_path):
            raise FileNotFoundError(f"File not found: {old_path}")
        if await self.exists(new_path):
            raise FileExistsError(f"File already exists: {new_path}")

        old_key = self._full_key(old_path)
        new_key = self._full_key(new_path)

        # Copy
        await asyncio.to_thread(
            self._client.copy_object,
            Bucket=self.bucket,
            CopySource={"Bucket": self.bucket, "Key": old_key},
            Key=new_key,
        )
        # Delete original
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self.bucket, Key=old_key
        )

    async def exists(self, path: str) -> bool:
        """Check if file exists using head_object (cheaper than get)."""
        key = self._full_key(path)
        try:
            await asyncio.to_thread(
                self._client.head_object, Bucket=self.bucket, Key=key
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise
