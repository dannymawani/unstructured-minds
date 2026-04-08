"""Word count plugin - adds word count to note metadata.

This is an example plugin demonstrating how to create plugins
for Unstructured Minds.
"""

import re
from typing import Any

from ..base import Plugin, PluginHook


class WordCountPlugin(Plugin):
    """Plugin that computes word count metadata for notes.

    This plugin registers for the METADATA_COMPUTE hook and adds
    word_count, character_count, and reading_time to note metadata.
    """

    name = "word_count"
    version = "1.0.0"
    description = "Adds word count, character count, and reading time to note metadata"
    author = "Unstructured Minds"

    # Average reading speed in words per minute
    WORDS_PER_MINUTE = 200

    async def on_load(self) -> None:
        """Register hooks when plugin loads."""
        self.register_hook(PluginHook.METADATA_COMPUTE, self.compute_metadata)
        self.register_hook(PluginHook.NOTE_AFTER_LOAD, self.enrich_note)

    async def on_unload(self) -> None:
        """Clean up when plugin unloads."""
        pass

    async def compute_metadata(
        self, data: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        """Compute word count metadata for a note.

        Args:
            data: Dictionary with 'content' key containing note text
            **kwargs: Additional arguments (unused)

        Returns:
            Updated data with metadata added
        """
        content = data.get("content", "")
        if not content:
            return data

        stats = self._compute_stats(content)

        # Add metadata to data
        if "metadata" not in data:
            data["metadata"] = {}

        data["metadata"].update(stats)
        return data

    async def enrich_note(
        self, data: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        """Enrich a loaded note with word count metadata.

        Args:
            data: Note data dictionary
            **kwargs: Additional arguments (unused)

        Returns:
            Note data with stats added
        """
        content = data.get("content", "")
        if not content:
            return data

        stats = self._compute_stats(content)
        data["stats"] = stats
        return data

    def _compute_stats(self, content: str) -> dict[str, Any]:
        """Compute statistics for content.

        Args:
            content: Text content to analyze

        Returns:
            Dictionary with word_count, character_count, reading_time_minutes
        """
        # Remove markdown formatting for cleaner count
        clean_content = self._strip_markdown(content)

        # Count words (split on whitespace)
        words = clean_content.split()
        word_count = len(words)

        # Count characters (excluding whitespace)
        character_count = len(clean_content.replace(" ", "").replace("\n", ""))

        # Calculate reading time
        reading_time = round(word_count / self.WORDS_PER_MINUTE, 1)

        # Count lines
        line_count = len(content.splitlines())

        return {
            "word_count": word_count,
            "character_count": character_count,
            "line_count": line_count,
            "reading_time_minutes": reading_time,
        }

    def _strip_markdown(self, content: str) -> str:
        """Remove common markdown formatting.

        Args:
            content: Markdown content

        Returns:
            Plain text content
        """
        # Remove code blocks
        content = re.sub(r"```[\s\S]*?```", "", content)
        content = re.sub(r"`[^`]+`", "", content)

        # Remove headers
        content = re.sub(r"^#+\s*", "", content, flags=re.MULTILINE)

        # Remove emphasis
        content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
        content = re.sub(r"\*([^*]+)\*", r"\1", content)
        content = re.sub(r"__([^_]+)__", r"\1", content)
        content = re.sub(r"_([^_]+)_", r"\1", content)

        # Remove links but keep text
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

        # Remove images
        content = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", content)

        # Remove horizontal rules
        content = re.sub(r"^[-*_]{3,}\s*$", "", content, flags=re.MULTILINE)

        # Remove list markers
        content = re.sub(r"^\s*[-*+]\s+", "", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*\d+\.\s+", "", content, flags=re.MULTILINE)

        # Remove checkboxes
        content = re.sub(r"\[[ x]\]\s*", "", content)

        return content.strip()
