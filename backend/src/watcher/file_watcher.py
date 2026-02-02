"""File watcher for vault changes."""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class MarkdownEventHandler(FileSystemEventHandler):
    """Handler for markdown file events."""

    def __init__(
        self,
        on_change: Callable[[str], None],
        debounce_seconds: float = 1.0,
    ) -> None:
        """Initialize handler.

        Args:
            on_change: Callback for file changes (receives relative path)
            debounce_seconds: Delay before triggering callback to debounce saves
        """
        super().__init__()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self._pending: dict[str, asyncio.TimerHandle] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for async callbacks."""
        self._loop = loop

    def _should_process(self, path: str) -> bool:
        """Check if file should be processed.

        Args:
            path: File path

        Returns:
            True if file should be processed
        """
        p = Path(path)
        # Only process markdown files
        if p.suffix.lower() != ".md":
            return False
        # Skip hidden files and directories
        if any(part.startswith(".") for part in p.parts):
            return False
        return True

    def _trigger_change(self, path: str) -> None:
        """Trigger the change callback.

        Args:
            path: File path that changed
        """
        if path in self._pending:
            del self._pending[path]
        self.on_change(path)

    def _schedule_change(self, path: str) -> None:
        """Schedule a debounced change callback.

        Args:
            path: File path that changed
        """
        if not self._loop:
            # No event loop, trigger immediately
            self.on_change(path)
            return

        # Cancel pending callback for this path
        if path in self._pending:
            self._pending[path].cancel()

        # Schedule new callback
        self._pending[path] = self._loop.call_later(
            self.debounce_seconds,
            self._trigger_change,
            path,
        )

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modified event."""
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            logger.debug(f"File modified: {event.src_path}")
            self._schedule_change(event.src_path)

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file created event."""
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            logger.debug(f"File created: {event.src_path}")
            self._schedule_change(event.src_path)


class FileWatcher:
    """Watches vault directory for file changes."""

    def __init__(
        self,
        vault_path: Path,
        on_change: Callable[[str], None],
        debounce_seconds: float = 1.0,
    ) -> None:
        """Initialize file watcher.

        Args:
            vault_path: Path to vault directory to watch
            on_change: Callback for file changes (receives relative path)
            debounce_seconds: Delay before triggering callback
        """
        self.vault_path = Path(vault_path).resolve()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self._observer: Optional[Observer] = None
        self._handler: Optional[MarkdownEventHandler] = None

    def _make_relative(self, absolute_path: str) -> str:
        """Convert absolute path to relative path from vault.

        Args:
            absolute_path: Absolute file path

        Returns:
            Path relative to vault
        """
        try:
            return str(Path(absolute_path).resolve().relative_to(self.vault_path))
        except ValueError:
            return absolute_path

    def _on_change_wrapper(self, path: str) -> None:
        """Wrapper to convert absolute paths to relative."""
        relative_path = self._make_relative(path)
        logger.info(f"Processing file change: {relative_path}")
        self.on_change(relative_path)

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start watching for file changes.

        Args:
            loop: Event loop for debouncing (optional)
        """
        if self._observer is not None:
            logger.warning("Watcher already running")
            return

        if not self.vault_path.exists():
            logger.warning(f"Vault path does not exist: {self.vault_path}")
            return

        self._handler = MarkdownEventHandler(
            on_change=self._on_change_wrapper,
            debounce_seconds=self.debounce_seconds,
        )
        if loop:
            self._handler.set_loop(loop)

        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.vault_path), recursive=True)
        self._observer.start()
        logger.info(f"Started watching vault: {self.vault_path}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self._observer is None:
            return

        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None
        self._handler = None
        logger.info("Stopped watching vault")

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._observer is not None and self._observer.is_alive()
