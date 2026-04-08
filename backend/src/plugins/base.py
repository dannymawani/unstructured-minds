"""Base plugin class and types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class PluginHook(StrEnum):
    """Available plugin hooks."""

    # Note lifecycle
    NOTE_BEFORE_SAVE = "note_before_save"
    NOTE_AFTER_SAVE = "note_after_save"
    NOTE_AFTER_LOAD = "note_after_load"

    # Extraction lifecycle
    EXTRACTION_BEFORE = "extraction_before"
    EXTRACTION_AFTER = "extraction_after"

    # Metadata hooks
    METADATA_COMPUTE = "metadata_compute"


@dataclass
class PluginInfo:
    """Plugin metadata."""

    name: str
    version: str
    description: str
    author: str = ""
    enabled: bool = False
    hooks: list[PluginHook] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "hooks": [h.value for h in self.hooks],
        }


class Plugin(ABC):
    """Base class for all plugins.

    Plugins must inherit from this class and implement the required methods.

    Example:
        class MyPlugin(Plugin):
            name = "my_plugin"
            version = "1.0.0"
            description = "My custom plugin"

            async def on_load(self) -> None:
                print("Plugin loaded!")

            async def on_unload(self) -> None:
                print("Plugin unloaded!")
    """

    # Required class attributes
    name: str = ""
    version: str = "0.0.0"
    description: str = ""
    author: str = ""

    def __init__(self) -> None:
        """Initialize plugin."""
        self._enabled = False
        self._hooks: dict[PluginHook, callable] = {}

    @property
    def info(self) -> PluginInfo:
        """Get plugin info."""
        return PluginInfo(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            enabled=self._enabled,
            hooks=list(self._hooks.keys()),
        )

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled

    def register_hook(self, hook: PluginHook, callback: callable) -> None:
        """Register a hook callback.

        Args:
            hook: The hook to register for
            callback: The callback function
        """
        self._hooks[hook] = callback

    def get_hook(self, hook: PluginHook) -> callable | None:
        """Get registered hook callback.

        Args:
            hook: The hook to get

        Returns:
            The callback if registered, None otherwise
        """
        return self._hooks.get(hook)

    @abstractmethod
    async def on_load(self) -> None:
        """Called when plugin is loaded.

        Override this to initialize your plugin.
        """
        pass

    @abstractmethod
    async def on_unload(self) -> None:
        """Called when plugin is unloaded.

        Override this to clean up resources.
        """
        pass

    async def on_enable(self) -> None:
        """Called when plugin is enabled.

        Override this for enable-specific logic.
        """
        self._enabled = True

    async def on_disable(self) -> None:
        """Called when plugin is disabled.

        Override this for disable-specific logic.
        """
        self._enabled = False
