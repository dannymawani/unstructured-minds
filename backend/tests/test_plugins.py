"""Tests for the plugin system."""

import json
import tempfile
from pathlib import Path

import pytest

from src.plugins.base import Plugin, PluginHook, PluginInfo
from src.plugins.manager import PluginManager


class TestPluginInfo:
    """Tests for PluginInfo dataclass."""

    def test_plugin_info_to_dict(self):
        """Test converting PluginInfo to dictionary."""
        info = PluginInfo(
            name="test_plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            enabled=True,
            hooks=[PluginHook.NOTE_AFTER_SAVE],
        )
        result = info.to_dict()

        assert result["name"] == "test_plugin"
        assert result["version"] == "1.0.0"
        assert result["description"] == "A test plugin"
        assert result["author"] == "Test Author"
        assert result["enabled"] is True
        assert result["hooks"] == ["note_after_save"]


class TestPlugin:
    """Tests for Plugin base class."""

    def test_plugin_info_property(self):
        """Test that plugin info property works."""

        class MyPlugin(Plugin):
            name = "my_plugin"
            version = "2.0.0"
            description = "My test plugin"

            async def on_load(self):
                pass

            async def on_unload(self):
                pass

        plugin = MyPlugin()
        info = plugin.info

        assert info.name == "my_plugin"
        assert info.version == "2.0.0"
        assert info.description == "My test plugin"
        assert info.enabled is False

    def test_register_and_get_hook(self):
        """Test registering and getting hooks."""

        class MyPlugin(Plugin):
            name = "hook_plugin"
            version = "1.0.0"

            async def on_load(self):
                self.register_hook(PluginHook.METADATA_COMPUTE, self.compute)

            async def on_unload(self):
                pass

            async def compute(self, data, **kwargs):
                return data

        plugin = MyPlugin()

        # Before registration
        assert plugin.get_hook(PluginHook.METADATA_COMPUTE) is None

        # Register hook manually
        plugin.register_hook(PluginHook.METADATA_COMPUTE, plugin.compute)

        # After registration
        assert plugin.get_hook(PluginHook.METADATA_COMPUTE) is not None


class TestPluginManager:
    """Tests for PluginManager."""

    @pytest.fixture
    def temp_state_path(self):
        """Create a temporary state file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "plugins.json"

    @pytest.fixture
    def manager(self, temp_state_path):
        """Create a plugin manager with temp state."""
        return PluginManager(temp_state_path)

    def test_manager_init_no_state_file(self, temp_state_path):
        """Test manager initialization without existing state."""
        manager = PluginManager(temp_state_path)
        assert manager.list_plugins() == []

    def test_manager_init_with_state_file(self, temp_state_path):
        """Test manager initialization with existing state."""
        temp_state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_state_path.write_text(json.dumps({"plugins": {"test": True}}))

        manager = PluginManager(temp_state_path)
        assert manager._state == {"test": True}

    def test_list_plugins_empty(self, manager):
        """Test listing plugins when none loaded."""
        assert manager.list_plugins() == []

    @pytest.mark.asyncio
    async def test_load_plugin_file_not_found(self, manager):
        """Test loading a non-existent plugin file."""
        result = await manager.load_plugin("/nonexistent/plugin.py")
        assert result is None

    @pytest.mark.asyncio
    async def test_load_plugin_not_python(self, manager):
        """Test loading a non-Python file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not python")
            result = await manager.load_plugin(f.name)
            assert result is None

    @pytest.mark.asyncio
    async def test_load_valid_plugin(self, manager):
        """Test loading a valid plugin."""
        plugin_code = '''
from src.plugins.base import Plugin

class TestPlugin(Plugin):
    name = "test_plugin"
    version = "1.0.0"
    description = "A test plugin"

    async def on_load(self):
        pass

    async def on_unload(self):
        pass
'''
        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w"
        ) as f:
            f.write(plugin_code)
            f.flush()
            result = await manager.load_plugin(f.name)

            assert result is not None
            assert result.name == "test_plugin"
            assert result.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_enable_disable_plugin(self, manager):
        """Test enabling and disabling a plugin."""
        # Create and load a plugin
        plugin_code = '''
from src.plugins.base import Plugin

class TogglePlugin(Plugin):
    name = "toggle_plugin"
    version = "1.0.0"

    async def on_load(self):
        pass

    async def on_unload(self):
        pass
'''
        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w"
        ) as f:
            f.write(plugin_code)
            f.flush()
            await manager.load_plugin(f.name)

        # Enable
        result = await manager.enable_plugin("toggle_plugin")
        assert result is True

        plugin = manager.get_plugin("toggle_plugin")
        assert plugin is not None
        assert plugin.enabled is True

        # Disable
        result = await manager.disable_plugin("toggle_plugin")
        assert result is True
        assert plugin.enabled is False

    @pytest.mark.asyncio
    async def test_enable_nonexistent_plugin(self, manager):
        """Test enabling a plugin that doesn't exist."""
        result = await manager.enable_plugin("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_hook(self, manager):
        """Test executing a hook across plugins."""
        # Create a plugin with a hook
        plugin_code = '''
from src.plugins.base import Plugin, PluginHook

class HookPlugin(Plugin):
    name = "hook_plugin"
    version = "1.0.0"

    async def on_load(self):
        self.register_hook(PluginHook.METADATA_COMPUTE, self.add_metadata)

    async def on_unload(self):
        pass

    async def add_metadata(self, data, **kwargs):
        data["processed"] = True
        return data
'''
        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w"
        ) as f:
            f.write(plugin_code)
            f.flush()
            await manager.load_plugin(f.name)

        # Enable the plugin
        await manager.enable_plugin("hook_plugin")

        # Execute hook
        data = {"content": "test"}
        result = await manager.execute_hook(PluginHook.METADATA_COMPUTE, data)

        assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_execute_hook_disabled_plugin_skipped(self, manager):
        """Test that disabled plugins are skipped during hook execution."""
        plugin_code = '''
from src.plugins.base import Plugin, PluginHook

class SkipPlugin(Plugin):
    name = "skip_plugin"
    version = "1.0.0"

    async def on_load(self):
        self.register_hook(PluginHook.METADATA_COMPUTE, self.add_metadata)

    async def on_unload(self):
        pass

    async def add_metadata(self, data, **kwargs):
        data["should_not_be_set"] = True
        return data
'''
        with tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w"
        ) as f:
            f.write(plugin_code)
            f.flush()
            await manager.load_plugin(f.name)

        # Don't enable the plugin

        # Execute hook
        data = {"content": "test"}
        result = await manager.execute_hook(PluginHook.METADATA_COMPUTE, data)

        assert "should_not_be_set" not in result


class TestWordCountPlugin:
    """Tests for the word count example plugin."""

    @pytest.mark.asyncio
    async def test_word_count_metadata(self):
        """Test word count plugin computes correct metadata."""
        from src.plugins.examples.word_count import WordCountPlugin

        plugin = WordCountPlugin()
        await plugin.on_load()
        await plugin.on_enable()

        # Test content
        data = {
            "content": "Hello world. This is a test note with some words."
        }

        # Execute hook directly
        callback = plugin.get_hook(PluginHook.METADATA_COMPUTE)
        assert callback is not None

        result = await callback(data)

        assert "metadata" in result
        assert result["metadata"]["word_count"] == 10
        assert result["metadata"]["reading_time_minutes"] == 0.1

    @pytest.mark.asyncio
    async def test_word_count_strips_markdown(self):
        """Test that markdown is stripped before counting."""
        from src.plugins.examples.word_count import WordCountPlugin

        plugin = WordCountPlugin()
        await plugin.on_load()

        # Test with markdown
        data = {
            "content": "# Header\n\n**Bold** and *italic* [link](http://example.com)"
        }

        callback = plugin.get_hook(PluginHook.METADATA_COMPUTE)
        result = await callback(data)

        # Should count: Header, Bold, and, italic, link = 5 words
        # (not the URL or markdown syntax)
        assert result["metadata"]["word_count"] == 5
