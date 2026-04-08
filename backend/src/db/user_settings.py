"""CRUD for per-user JSON settings stored in Postgres user_settings table."""

import json
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


class UserSettingsStore:
    """Read/write per-user JSONB settings from the Postgres user_settings table.

    Each setting is identified by a (user_id, key) pair where value is JSONB.
    """

    def __init__(self, db, user_id: str) -> None:
        self._db = db
        self._user_id = user_id

    def get(self, key: str) -> dict[str, Any] | None:
        """Read a settings value by key.

        Returns None if not found.
        """
        result = self._db.execute(
            "SELECT value FROM user_settings WHERE user_id = %s AND key = %s",
            [self._user_id, key],
        ).fetchone()
        if result and result[0] is not None:
            val = result[0]
            # psycopg3 returns JSONB as dict/list automatically, but handle string too
            if isinstance(val, str):
                return json.loads(val)
            return val
        return None

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Upsert a settings value."""
        json_value = json.dumps(value, ensure_ascii=False)
        self._db.execute(
            """
            INSERT INTO user_settings (user_id, key, value, updated_at)
            VALUES (%s, %s, %s::jsonb, NOW())
            ON CONFLICT (user_id, key) DO UPDATE
            SET value = EXCLUDED.value, updated_at = NOW()
            """,
            [self._user_id, key, json_value],
        )

    def delete(self, key: str) -> bool:
        """Delete a settings entry. Returns True if it existed."""
        result = self._db.execute(
            "DELETE FROM user_settings WHERE user_id = %s AND key = %s RETURNING key",
            [self._user_id, key],
        ).fetchone()
        return result is not None

    def list_keys(self) -> list[str]:
        """List all setting keys for this user."""
        rows = self._db.execute(
            "SELECT key FROM user_settings WHERE user_id = %s ORDER BY key",
            [self._user_id],
        ).fetchall()
        return [row[0] for row in rows]
