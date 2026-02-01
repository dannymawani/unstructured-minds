"""Tests for storage abstraction layer."""

import pytest
from pathlib import Path

from src.storage import LocalFilesystem, StorageBackend, get_storage_backend


@pytest.fixture
def storage(tmp_path: Path) -> LocalFilesystem:
    """Create a LocalFilesystem storage backend for testing."""
    return LocalFilesystem(base_path=tmp_path)


class TestLocalFilesystem:
    """Tests for LocalFilesystem backend."""

    async def test_write_and_read(self, storage: LocalFilesystem) -> None:
        """Test writing and reading a file."""
        await storage.write("test.md", b"# Hello")
        content = await storage.read("test.md")
        assert content == b"# Hello"

    async def test_read_nonexistent_file(self, storage: LocalFilesystem) -> None:
        """Test reading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await storage.read("nonexistent.md")

    async def test_write_creates_directories(self, storage: LocalFilesystem) -> None:
        """Test that write creates parent directories."""
        await storage.write("a/b/c/test.md", b"nested")
        content = await storage.read("a/b/c/test.md")
        assert content == b"nested"

    async def test_list_files(self, storage: LocalFilesystem) -> None:
        """Test listing files."""
        await storage.write("a.md", b"a")
        await storage.write("b.md", b"b")
        await storage.write("dir/c.md", b"c")

        files = await storage.list("")
        assert set(files) == {"a.md", "b.md", "dir/c.md"}

    async def test_list_with_prefix(self, storage: LocalFilesystem) -> None:
        """Test listing files with prefix filter."""
        await storage.write("Daily-Notes/2026-01/01.md", b"day1")
        await storage.write("Daily-Notes/2026-01/02.md", b"day2")
        await storage.write("Training/workout.md", b"workout")

        files = await storage.list("Daily-Notes")
        assert len(files) == 2
        assert all("Daily-Notes" in f for f in files)

    async def test_delete(self, storage: LocalFilesystem) -> None:
        """Test deleting a file."""
        await storage.write("delete-me.md", b"bye")
        assert await storage.exists("delete-me.md")

        await storage.delete("delete-me.md")
        assert not await storage.exists("delete-me.md")

    async def test_delete_nonexistent_file(self, storage: LocalFilesystem) -> None:
        """Test deleting a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await storage.delete("nonexistent.md")

    async def test_exists(self, storage: LocalFilesystem) -> None:
        """Test checking if file exists."""
        assert not await storage.exists("test.md")

        await storage.write("test.md", b"content")
        assert await storage.exists("test.md")

    async def test_path_traversal_blocked(self, storage: LocalFilesystem) -> None:
        """Test that path traversal is blocked."""
        with pytest.raises(ValueError, match="escapes base directory"):
            await storage.read("../../../etc/passwd")


class TestStorageFactory:
    """Tests for storage backend factory."""

    def test_get_local_backend(self, tmp_path: Path) -> None:
        """Test getting local filesystem backend."""
        backend = get_storage_backend("local", base_path=tmp_path)
        assert isinstance(backend, LocalFilesystem)
        assert isinstance(backend, StorageBackend)

    def test_invalid_backend_type(self) -> None:
        """Test that invalid backend type raises error."""
        with pytest.raises(ValueError, match="Unsupported"):
            get_storage_backend("invalid")
