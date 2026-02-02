"""Tests for file watcher module."""

import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.watcher import FileWatcher
from src.watcher.file_watcher import MarkdownEventHandler


class TestMarkdownEventHandler:
    """Tests for MarkdownEventHandler."""

    def test_should_process_markdown_files(self):
        """Test that markdown files are processed."""
        handler = MarkdownEventHandler(on_change=MagicMock())

        assert handler._should_process("/path/to/note.md")
        assert handler._should_process("/path/to/NOTE.MD")
        assert handler._should_process("daily.md")

    def test_should_skip_non_markdown_files(self):
        """Test that non-markdown files are skipped."""
        handler = MarkdownEventHandler(on_change=MagicMock())

        assert not handler._should_process("/path/to/file.txt")
        assert not handler._should_process("/path/to/file.py")
        assert not handler._should_process("/path/to/file")

    def test_should_skip_hidden_files(self):
        """Test that hidden files are skipped."""
        handler = MarkdownEventHandler(on_change=MagicMock())

        assert not handler._should_process("/path/.hidden.md")
        assert not handler._should_process("/path/.git/note.md")
        assert not handler._should_process(".obsidian/plugins.md")

    def test_on_modified_triggers_callback(self):
        """Test that file modification triggers callback."""
        callback = MagicMock()
        handler = MarkdownEventHandler(on_change=callback)

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/note.md"

        handler.on_modified(event)

        callback.assert_called_once_with("/path/to/note.md")

    def test_on_created_triggers_callback(self):
        """Test that file creation triggers callback."""
        callback = MagicMock()
        handler = MarkdownEventHandler(on_change=callback)

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/new.md"

        handler.on_created(event)

        callback.assert_called_once_with("/path/to/new.md")

    def test_ignores_directory_events(self):
        """Test that directory events are ignored."""
        callback = MagicMock()
        handler = MarkdownEventHandler(on_change=callback)

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/path/to/dir"

        handler.on_modified(event)
        handler.on_created(event)

        callback.assert_not_called()


class TestFileWatcher:
    """Tests for FileWatcher."""

    def test_init(self, tmp_path: Path):
        """Test watcher initialization."""
        watcher = FileWatcher(
            vault_path=tmp_path,
            on_change=MagicMock(),
        )

        assert watcher.vault_path == tmp_path.resolve()
        assert not watcher.is_running

    def test_start_and_stop(self, tmp_path: Path):
        """Test starting and stopping the watcher."""
        watcher = FileWatcher(
            vault_path=tmp_path,
            on_change=MagicMock(),
        )

        watcher.start()
        assert watcher.is_running

        watcher.stop()
        assert not watcher.is_running

    def test_start_nonexistent_path(self, tmp_path: Path):
        """Test starting watcher on non-existent path."""
        nonexistent = tmp_path / "nonexistent"
        watcher = FileWatcher(
            vault_path=nonexistent,
            on_change=MagicMock(),
        )

        watcher.start()
        assert not watcher.is_running

    def test_make_relative_path(self, tmp_path: Path):
        """Test converting absolute to relative paths."""
        watcher = FileWatcher(
            vault_path=tmp_path,
            on_change=MagicMock(),
        )

        absolute = str(tmp_path / "Daily-Notes" / "2026-02-02.md")
        relative = watcher._make_relative(absolute)

        assert relative == "Daily-Notes/2026-02-02.md"

    def test_detects_file_changes(self, tmp_path: Path):
        """Test that file changes are detected."""
        changes = []
        watcher = FileWatcher(
            vault_path=tmp_path,
            on_change=lambda p: changes.append(p),
            debounce_seconds=0.1,
        )

        watcher.start()
        try:
            # Create a file
            test_file = tmp_path / "test.md"
            test_file.write_text("# Test")

            # Wait for detection
            time.sleep(0.5)

            # Verify change was detected
            assert len(changes) > 0
            assert "test.md" in changes[0]
        finally:
            watcher.stop()

    def test_ignores_non_markdown_files(self, tmp_path: Path):
        """Test that non-markdown files are ignored."""
        changes = []
        watcher = FileWatcher(
            vault_path=tmp_path,
            on_change=lambda p: changes.append(p),
            debounce_seconds=0.1,
        )

        watcher.start()
        try:
            # Create a non-markdown file
            test_file = tmp_path / "test.txt"
            test_file.write_text("test")

            # Wait for potential detection
            time.sleep(0.3)

            # Verify no changes detected
            assert len(changes) == 0
        finally:
            watcher.stop()

    def test_double_start_warning(self, tmp_path: Path, caplog):
        """Test that starting twice logs a warning."""
        watcher = FileWatcher(
            vault_path=tmp_path,
            on_change=MagicMock(),
        )

        watcher.start()
        watcher.start()

        assert "already running" in caplog.text.lower()

        watcher.stop()

    def test_stop_when_not_running(self, tmp_path: Path):
        """Test that stopping when not running is safe."""
        watcher = FileWatcher(
            vault_path=tmp_path,
            on_change=MagicMock(),
        )

        # Should not raise
        watcher.stop()
        assert not watcher.is_running
