"""Plugin manager for loading and managing plugins."""

import importlib.util
import json
import logging
import sys
import types
from pathlib import Path
from typing import Any, Optional

from .base import Plugin, PluginHook, PluginInfo

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin loading, enabling, and lifecycle.

    The plugin manager handles:
    - Loading plugins from Python files
    - Persisting plugin state to JSON
    - Enabling/disabling plugins
    - Executing plugin hooks
    """

    def __init__(self, plugins_state_path: Path) -> None:
        """Initialize the plugin manager.

        Args:
            plugins_state_path: Path to the plugins.json state file
        """
        self._plugins: dict[str, Plugin] = {}
        self._state_path = plugins_state_path
        self._state: dict[str, bool] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load plugin enabled/disabled state from JSON."""
        if self._state_path.exists():
            try:
                with open(self._state_path) as f:
                    data = json.load(f)
                    self._state = data.get("plugins", {})
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load plugin state: {e}")
                self._state = {}

    def _save_state(self) -> None:
        """Save plugin state to JSON."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._state_path, "w") as f:
                json.dump({"plugins": self._state}, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save plugin state: {e}")

    async def load_plugin(self, path: str) -> Optional[PluginInfo]:
        """Load a plugin from a Python file.

        Args:
            path: Path to the plugin Python file

        Returns:
            PluginInfo if successful, None otherwise
        """
        plugin_path = Path(path)
        if not plugin_path.exists():
            logger.error(f"Plugin file not found: {path}")
            return None

        if not plugin_path.suffix == ".py":
            logger.error(f"Plugin must be a Python file: {path}")
            return None

        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(
                plugin_path.stem, plugin_path
            )
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load plugin spec: {path}")
                return None

            module = importlib.util.module_from_spec(spec)

            # Set up package context so relative imports work
            plugins_root = Path(__file__).resolve().parent
            try:
                rel = plugin_path.resolve().parent.relative_to(plugins_root)
                base_pkg = __name__.rsplit(".", 1)[0]  # e.g. "src.plugins"
                pkg = f"{base_pkg}.{'.'.join(rel.parts)}" if rel.parts else base_pkg
                module.__package__ = pkg
                if pkg not in sys.modules:
                    pkg_mod = types.ModuleType(pkg)
                    pkg_mod.__package__ = pkg
                    pkg_mod.__path__ = [str(plugin_path.parent)]
                    sys.modules[pkg] = pkg_mod
            except ValueError:
                pass  # Plugin outside plugins dir; relative imports won't work

            spec.loader.exec_module(module)

            # Find Plugin subclass in module
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Plugin)
                    and attr is not Plugin
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                logger.error(f"No Plugin subclass found in: {path}")
                return None

            # Instantiate plugin
            plugin = plugin_class()

            if not plugin.name:
                logger.error(f"Plugin has no name: {path}")
                return None

            # Store plugin
            self._plugins[plugin.name] = plugin

            # Call on_load
            await plugin.on_load()
            logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")

            # Restore enabled state if previously enabled
            if self._state.get(plugin.name, False):
                await self.enable_plugin(plugin.name)

            return plugin.info

        except Exception as e:
            logger.error(f"Failed to load plugin {path}: {e}")
            return None

    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name.

        Args:
            name: Plugin name

        Returns:
            True if successful
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            return False

        try:
            if plugin.enabled:
                await plugin.on_disable()
            await plugin.on_unload()
            del self._plugins[name]
            logger.info(f"Unloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return False

    def list_plugins(self) -> list[PluginInfo]:
        """List all loaded plugins.

        Returns:
            List of plugin info objects
        """
        return [plugin.info for plugin in self._plugins.values()]

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin if found, None otherwise
        """
        return self._plugins.get(name)

    async def enable_plugin(self, name: str) -> bool:
        """Enable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if successful
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning(f"Plugin not found: {name}")
            return False

        if plugin.enabled:
            return True

        try:
            await plugin.on_enable()
            self._state[name] = True
            self._save_state()
            logger.info(f"Enabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}")
            return False

    async def disable_plugin(self, name: str) -> bool:
        """Disable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if successful
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning(f"Plugin not found: {name}")
            return False

        if not plugin.enabled:
            return True

        try:
            await plugin.on_disable()
            self._state[name] = False
            self._save_state()
            logger.info(f"Disabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}")
            return False

    async def execute_hook(
        self, hook: PluginHook, data: Any, **kwargs: Any
    ) -> Any:
        """Execute a hook across all enabled plugins.

        Args:
            hook: The hook to execute
            data: Data to pass to the hook
            **kwargs: Additional arguments for the hook

        Returns:
            Modified data after all hooks have processed
        """
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue

            callback = plugin.get_hook(hook)
            if callback is None:
                continue

            try:
                result = await callback(data, **kwargs)
                if result is not None:
                    data = result
            except Exception as e:
                logger.error(
                    f"Plugin {plugin.name} failed on hook {hook.value}: {e}"
                )

        return data

    async def load_builtin_plugins(self, plugins_dir: Path) -> None:
        """Load all built-in plugins from a directory.

        Args:
            plugins_dir: Directory containing plugin files
        """
        if not plugins_dir.exists():
            logger.debug(f"Plugins directory not found: {plugins_dir}")
            return

        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            await self.load_plugin(str(plugin_file))
