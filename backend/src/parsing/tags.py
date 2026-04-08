"""Tag and wiki-link extraction from markdown content.

Supports:
- #tags: Hashtag-style tags like #project, #todo-item, #2024
- [[wiki-links]]: Wiki-style links like [[My Note]], [[folder/note]]
"""

import re
from typing import NamedTuple

# Pattern for #tags
# - Must start with # followed by a letter
# - Can contain letters, numbers, underscores, and hyphens
# - Cannot be in a code block or inline code
TAG_PATTERN = re.compile(r"(?<![`\w])#([a-zA-Z][a-zA-Z0-9_-]*)\b")

# Pattern for [[wiki-links]]
# - Matches anything between [[ and ]]
# - The link text can contain any characters except ]
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")

# Pattern to detect code blocks (fenced or indented)
CODE_BLOCK_PATTERN = re.compile(
    r"```[\s\S]*?```|`[^`]+`",
    re.MULTILINE,
)


class ParsedContent(NamedTuple):
    """Result of parsing markdown content for tags and links."""

    tags: list[str]
    wiki_links: list[str]


def _remove_code_blocks(content: str) -> str:
    """Remove code blocks and inline code from content.

    Args:
        content: Markdown content

    Returns:
        Content with code sections replaced by spaces
    """
    return CODE_BLOCK_PATTERN.sub(
        lambda m: " " * len(m.group(0)),
        content,
    )


def extract_tags(content: str) -> list[str]:
    """Extract unique #tags from markdown content.

    Tags must:
    - Start with # followed by a letter
    - Contain only letters, numbers, underscores, and hyphens
    - Not be inside code blocks or inline code

    Args:
        content: Markdown content to parse

    Returns:
        List of unique tags (without the # prefix), sorted alphabetically
    """
    # Remove code blocks to avoid matching tags in code
    clean_content = _remove_code_blocks(content)

    # Find all tags
    matches = TAG_PATTERN.findall(clean_content)

    # Return unique tags, sorted
    return sorted(set(matches))


def extract_wiki_links(content: str) -> list[str]:
    """Extract unique [[wiki-links]] from markdown content.

    Links can contain any text including paths like [[folder/note]].

    Args:
        content: Markdown content to parse

    Returns:
        List of unique link targets (without the [[ ]] brackets), sorted
    """
    # Remove code blocks to avoid matching links in code
    clean_content = _remove_code_blocks(content)

    # Find all wiki links
    matches = WIKI_LINK_PATTERN.findall(clean_content)

    # Return unique links, sorted
    return sorted(set(matches))


def parse_markdown_for_links(content: str) -> ParsedContent:
    """Parse markdown content for both tags and wiki-links.

    Args:
        content: Markdown content to parse

    Returns:
        ParsedContent with tags and wiki_links lists
    """
    return ParsedContent(
        tags=extract_tags(content),
        wiki_links=extract_wiki_links(content),
    )


def normalize_link_target(link_target: str) -> str:
    """Normalize a wiki-link target to a file path.

    Handles:
    - Adding .md extension if missing
    - Normalizing path separators

    Args:
        link_target: The text inside [[...]]

    Returns:
        Normalized file path
    """
    # Strip whitespace
    target = link_target.strip()

    # Handle display text (e.g., [[path|display text]])
    if "|" in target:
        target = target.split("|")[0].strip()

    # Handle anchors (e.g., [[note#section]])
    if "#" in target:
        target = target.split("#")[0].strip()

    # Normalize path separators
    target = target.replace("\\", "/")

    # Add .md extension if missing
    if not target.endswith(".md"):
        target = target + ".md"

    return target
