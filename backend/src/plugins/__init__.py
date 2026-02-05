"""Plugin system for Unstructured Minds."""

from .base import Plugin, PluginInfo, PluginHook
from .manager import PluginManager

__all__ = ["Plugin", "PluginInfo", "PluginHook", "PluginManager"]
