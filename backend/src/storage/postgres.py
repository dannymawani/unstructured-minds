"""Postgres-backed storage backend using the vault_files table."""

import hashlib

from ..logging_config import get_logger

logger = get_logger(__name__)


class PostgresStorage:
    """Storage backend that stores files in the Postgres vault_files table.

    Implements the StorageBackend protocol. All content is stored as TEXT
    (UTF-8 markdown), but the protocol interface uses bytes for compatibility.
    """

    def __init__(self, pg, user_id: str, path_prefix: str = "") -> None:
        self._pg = pg
        self._user_id = user_id
        self._prefix = path_prefix.strip("/")

    def _full_path(self, path: str) -> str:
        path = path.lstrip("/")
        if self._prefix:
            return f"{self._prefix}/{path}"
        return path

    def _strip_prefix(self, path: str) -> str:
        if self._prefix and path.startswith(f"{self._prefix}/"):
            return path[len(self._prefix) + 1 :]
        return path

    async def read(self, path: str) -> bytes:
        full = self._full_path(path)
        result = self._pg.execute(
            "SELECT content FROM vault_files WHERE user_id = %s AND path = %s",
            [self._user_id, full],
        ).fetchone()
        if not result:
            raise FileNotFoundError(f"File not found: {path}")
        return result[0].encode("utf-8")

    async def write(self, path: str, content: bytes) -> None:
        full = self._full_path(path)
        text = content.decode("utf-8")
        size = len(content)
        content_hash = hashlib.sha256(content).hexdigest()
        self._pg.execute(
            """
            INSERT INTO vault_files (user_id, path, content, size_bytes, content_hash, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id, path) DO UPDATE
            SET content = EXCLUDED.content,
                size_bytes = EXCLUDED.size_bytes,
                content_hash = EXCLUDED.content_hash,
                updated_at = NOW()
            """,
            [self._user_id, full, text, size, content_hash],
        )

    async def delete(self, path: str) -> None:
        full = self._full_path(path)
        result = self._pg.execute(
            "DELETE FROM vault_files WHERE user_id = %s AND path = %s RETURNING path",
            [self._user_id, full],
        ).fetchone()
        if not result:
            raise FileNotFoundError(f"File not found: {path}")

    async def list(self, prefix: str = "") -> list[str]:
        search = self._full_path(prefix) if prefix else (self._prefix + "/" if self._prefix else "")
        result = self._pg.execute(
            "SELECT path FROM vault_files WHERE user_id = %s AND path LIKE %s ORDER BY path",
            [self._user_id, f"{search}%"],
        ).fetchall()
        paths = []
        for (p,) in result:
            relative = self._strip_prefix(p)
            if relative:
                paths.append(relative)
        return paths

    async def rename(self, old_path: str, new_path: str) -> None:
        if not await self.exists(old_path):
            raise FileNotFoundError(f"File not found: {old_path}")
        if await self.exists(new_path):
            raise FileExistsError(f"File already exists: {new_path}")
        old_full = self._full_path(old_path)
        new_full = self._full_path(new_path)
        self._pg.execute(
            "UPDATE vault_files SET path = %s, updated_at = NOW() WHERE user_id = %s AND path = %s",
            [new_full, self._user_id, old_full],
        )

    async def exists(self, path: str) -> bool:
        full = self._full_path(path)
        result = self._pg.execute(
            "SELECT 1 FROM vault_files WHERE user_id = %s AND path = %s",
            [self._user_id, full],
        ).fetchone()
        return result is not None
