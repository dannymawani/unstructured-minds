"""Tests for PostgresStorage backend using a mock PostgresManager."""

import pytest

from src.storage.postgres import PostgresStorage


TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


class FakePgResult:
    """Mimics _PgResult from PostgresManager."""

    def __init__(self, rows: list[tuple]):
        self._rows = rows

    def fetchall(self) -> list[tuple]:
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakePg:
    """In-memory fake of PostgresManager backed by a dict."""

    def __init__(self):
        self._store: dict[tuple[str, str], dict] = {}

    def execute(self, query: str, params: list | None = None) -> FakePgResult:
        params = params or []
        q = query.strip().upper()

        if q.startswith("SELECT CONTENT"):
            user_id, path = params[0], params[1]
            key = (user_id, path)
            if key in self._store:
                return FakePgResult([(self._store[key]["content"],)])
            return FakePgResult([])

        elif q.startswith("SELECT 1"):
            user_id, path = params[0], params[1]
            key = (user_id, path)
            if key in self._store:
                return FakePgResult([(1,)])
            return FakePgResult([])

        elif q.startswith("SELECT PATH"):
            user_id, like_pattern = params[0], params[1]
            prefix = like_pattern.rstrip("%")
            matches = []
            for (uid, p), _row in sorted(self._store.items()):
                if uid == user_id and p.startswith(prefix):
                    matches.append((p,))
            return FakePgResult(matches)

        elif q.startswith("INSERT INTO VAULT_FILES"):
            user_id, path, content, size, content_hash = params[0], params[1], params[2], params[3], params[4]
            self._store[(user_id, path)] = {
                "content": content,
                "size_bytes": size,
                "content_hash": content_hash,
            }
            return FakePgResult([])

        elif q.startswith("DELETE FROM VAULT_FILES"):
            user_id, path = params[0], params[1]
            key = (user_id, path)
            if key in self._store:
                del self._store[key]
                return FakePgResult([(path,)])
            return FakePgResult([])

        elif q.startswith("UPDATE VAULT_FILES"):
            new_path, user_id, old_path = params[0], params[1], params[2]
            old_key = (user_id, old_path)
            if old_key in self._store:
                data = self._store.pop(old_key)
                self._store[(user_id, new_path)] = data
            return FakePgResult([])

        return FakePgResult([])


@pytest.fixture
def pg():
    return FakePg()


@pytest.fixture
def storage(pg):
    return PostgresStorage(pg, TEST_USER_ID)


@pytest.fixture
def prefixed_storage(pg):
    return PostgresStorage(pg, TEST_USER_ID, path_prefix="_data")


class TestPostgresStorage:
    async def test_write_and_read(self, storage):
        await storage.write("test.md", b"# Hello")
        content = await storage.read("test.md")
        assert content == b"# Hello"

    async def test_read_nonexistent(self, storage):
        with pytest.raises(FileNotFoundError):
            await storage.read("nonexistent.md")

    async def test_write_overwrite(self, storage):
        await storage.write("test.md", b"v1")
        await storage.write("test.md", b"v2")
        content = await storage.read("test.md")
        assert content == b"v2"

    async def test_delete(self, storage):
        await storage.write("delete-me.md", b"bye")
        assert await storage.exists("delete-me.md")
        await storage.delete("delete-me.md")
        assert not await storage.exists("delete-me.md")

    async def test_delete_nonexistent(self, storage):
        with pytest.raises(FileNotFoundError):
            await storage.delete("nonexistent.md")

    async def test_exists(self, storage):
        assert not await storage.exists("test.md")
        await storage.write("test.md", b"content")
        assert await storage.exists("test.md")

    async def test_list_files(self, storage):
        await storage.write("a.md", b"a")
        await storage.write("b.md", b"b")
        await storage.write("dir/c.md", b"c")
        files = await storage.list("")
        assert set(files) == {"a.md", "b.md", "dir/c.md"}

    async def test_list_with_prefix(self, storage):
        await storage.write("Daily-Notes/2026-01/01.md", b"day1")
        await storage.write("Daily-Notes/2026-01/02.md", b"day2")
        await storage.write("Training/workout.md", b"workout")
        files = await storage.list("Daily-Notes")
        assert len(files) == 2
        assert all("Daily-Notes" in f for f in files)

    async def test_rename(self, storage):
        await storage.write("old.md", b"# Old")
        await storage.rename("old.md", "new.md")
        assert not await storage.exists("old.md")
        assert await storage.exists("new.md")
        content = await storage.read("new.md")
        assert content == b"# Old"

    async def test_rename_nonexistent(self, storage):
        with pytest.raises(FileNotFoundError):
            await storage.rename("nonexistent.md", "new.md")

    async def test_rename_dest_exists(self, storage):
        await storage.write("a.md", b"a")
        await storage.write("b.md", b"b")
        with pytest.raises(FileExistsError):
            await storage.rename("a.md", "b.md")


class TestPostgresStoragePrefixed:
    async def test_write_and_read_with_prefix(self, prefixed_storage, pg):
        await prefixed_storage.write("settings.json", b'{"theme":"dark"}')
        content = await prefixed_storage.read("settings.json")
        assert content == b'{"theme":"dark"}'
        # Verify stored under prefixed key
        assert ("00000000-0000-0000-0000-000000000001", "_data/settings.json") in pg._store

    async def test_list_only_own_prefix(self, prefixed_storage, pg):
        await prefixed_storage.write("a.json", b"{}")
        # Write directly under a different prefix
        pg._store[("00000000-0000-0000-0000-000000000001", "other/b.json")] = {
            "content": "{}", "size_bytes": 2, "content_hash": "x"
        }
        files = await prefixed_storage.list("")
        assert files == ["a.json"]

    async def test_exists_with_prefix(self, prefixed_storage):
        assert not await prefixed_storage.exists("test.json")
        await prefixed_storage.write("test.json", b"{}")
        assert await prefixed_storage.exists("test.json")
