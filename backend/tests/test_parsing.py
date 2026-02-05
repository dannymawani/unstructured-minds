"""Tests for parsing utilities (tags and wiki-links)."""

import pytest

from src.parsing import (
    extract_tags,
    extract_wiki_links,
    parse_markdown_for_links,
    normalize_link_target,
    TAG_PATTERN,
    WIKI_LINK_PATTERN,
)


class TestExtractTags:
    """Tests for extract_tags function."""

    def test_extracts_simple_tag(self) -> None:
        """Test extracting a simple tag."""
        content = "This is a note with #project tag."
        tags = extract_tags(content)
        assert tags == ["project"]

    def test_extracts_multiple_tags(self) -> None:
        """Test extracting multiple tags."""
        content = "Note with #project and #todo tags."
        tags = extract_tags(content)
        assert tags == ["project", "todo"]

    def test_extracts_tags_with_numbers(self) -> None:
        """Test tags can contain numbers after the first letter."""
        content = "Year tag: #year2024"
        tags = extract_tags(content)
        assert tags == ["year2024"]

    def test_extracts_tags_with_hyphens(self) -> None:
        """Test tags can contain hyphens."""
        content = "A #todo-item for later."
        tags = extract_tags(content)
        assert tags == ["todo-item"]

    def test_extracts_tags_with_underscores(self) -> None:
        """Test tags can contain underscores."""
        content = "A #work_project reference."
        tags = extract_tags(content)
        assert tags == ["work_project"]

    def test_tag_must_start_with_letter(self) -> None:
        """Test tags must start with a letter, not a number."""
        content = "Not a tag: #123number"
        tags = extract_tags(content)
        assert tags == []

    def test_removes_duplicate_tags(self) -> None:
        """Test duplicate tags are removed."""
        content = "#project is great. Back to #project again."
        tags = extract_tags(content)
        assert tags == ["project"]

    def test_returns_sorted_tags(self) -> None:
        """Test tags are returned in sorted order."""
        content = "#zebra then #apple then #mango"
        tags = extract_tags(content)
        assert tags == ["apple", "mango", "zebra"]

    def test_ignores_tags_in_inline_code(self) -> None:
        """Test tags inside inline code are ignored."""
        content = "Real #tag but `#not-a-tag` in code."
        tags = extract_tags(content)
        assert tags == ["tag"]

    def test_ignores_tags_in_code_blocks(self) -> None:
        """Test tags inside fenced code blocks are ignored."""
        content = """
#real-tag here.

```python
# This #code-tag should be ignored
print("hello")
```

And #another-tag.
"""
        tags = extract_tags(content)
        assert tags == ["another-tag", "real-tag"]

    def test_handles_empty_content(self) -> None:
        """Test empty content returns empty list."""
        tags = extract_tags("")
        assert tags == []

    def test_handles_no_tags(self) -> None:
        """Test content without tags returns empty list."""
        content = "This note has no hashtags."
        tags = extract_tags(content)
        assert tags == []

    def test_tag_at_start_of_line(self) -> None:
        """Test tag at the start of a line."""
        content = "#project\nSome text."
        tags = extract_tags(content)
        assert tags == ["project"]

    def test_tag_at_end_of_line(self) -> None:
        """Test tag at the end of a line."""
        content = "Some text #project"
        tags = extract_tags(content)
        assert tags == ["project"]

    def test_tag_not_in_word(self) -> None:
        """Test tag must not be part of a larger word."""
        content = "email@example#com is not a tag"
        tags = extract_tags(content)
        assert tags == []


class TestExtractWikiLinks:
    """Tests for extract_wiki_links function."""

    def test_extracts_simple_link(self) -> None:
        """Test extracting a simple wiki link."""
        content = "See [[My Note]] for details."
        links = extract_wiki_links(content)
        assert links == ["My Note"]

    def test_extracts_multiple_links(self) -> None:
        """Test extracting multiple wiki links."""
        content = "Links to [[Note A]] and [[Note B]]."
        links = extract_wiki_links(content)
        assert links == ["Note A", "Note B"]

    def test_extracts_links_with_paths(self) -> None:
        """Test links can contain folder paths."""
        content = "See [[folder/subfolder/note]]."
        links = extract_wiki_links(content)
        assert links == ["folder/subfolder/note"]

    def test_extracts_links_with_display_text(self) -> None:
        """Test links with display text (pipe syntax)."""
        content = "See [[actual-note|Display Text]]."
        links = extract_wiki_links(content)
        assert links == ["actual-note|Display Text"]

    def test_extracts_links_with_anchors(self) -> None:
        """Test links with section anchors."""
        content = "See [[Note#Section]]."
        links = extract_wiki_links(content)
        assert links == ["Note#Section"]

    def test_removes_duplicate_links(self) -> None:
        """Test duplicate links are removed."""
        content = "See [[Note]] and then [[Note]] again."
        links = extract_wiki_links(content)
        assert links == ["Note"]

    def test_returns_sorted_links(self) -> None:
        """Test links are returned in sorted order."""
        content = "[[Zebra]] [[Apple]] [[Mango]]"
        links = extract_wiki_links(content)
        assert links == ["Apple", "Mango", "Zebra"]

    def test_ignores_links_in_code_blocks(self) -> None:
        """Test links in code blocks are ignored."""
        content = """
Real [[link]] here.

```
[[code-link]] should be ignored
```

Another [[real-link]].
"""
        links = extract_wiki_links(content)
        assert links == ["link", "real-link"]

    def test_ignores_links_in_inline_code(self) -> None:
        """Test links in inline code are ignored."""
        content = "Real [[link]] but `[[not-a-link]]` in code."
        links = extract_wiki_links(content)
        assert links == ["link"]

    def test_handles_empty_content(self) -> None:
        """Test empty content returns empty list."""
        links = extract_wiki_links("")
        assert links == []

    def test_handles_no_links(self) -> None:
        """Test content without links returns empty list."""
        content = "This note has no wiki links."
        links = extract_wiki_links(content)
        assert links == []

    def test_link_with_special_characters(self) -> None:
        """Test links can contain special characters."""
        content = "See [[Meeting 2024-01-15]]."
        links = extract_wiki_links(content)
        assert links == ["Meeting 2024-01-15"]


class TestParseMarkdownForLinks:
    """Tests for parse_markdown_for_links function."""

    def test_returns_both_tags_and_links(self) -> None:
        """Test function returns both tags and wiki links."""
        content = "Note with #tag and [[link]]."
        result = parse_markdown_for_links(content)
        assert result.tags == ["tag"]
        assert result.wiki_links == ["link"]

    def test_handles_complex_content(self) -> None:
        """Test with complex content including code blocks."""
        content = """
# My Note

#project #todo

Links to [[Other Note]] and [[Another One]].

```python
# #code-tag and [[code-link]]
print("hello")
```

More #tags here with [[Real Link]].
"""
        result = parse_markdown_for_links(content)
        assert set(result.tags) == {"project", "tags", "todo"}
        assert set(result.wiki_links) == {"Another One", "Other Note", "Real Link"}


class TestNormalizeLinkTarget:
    """Tests for normalize_link_target function."""

    def test_adds_md_extension(self) -> None:
        """Test .md extension is added if missing."""
        assert normalize_link_target("My Note") == "My Note.md"

    def test_preserves_existing_extension(self) -> None:
        """Test existing .md extension is preserved."""
        assert normalize_link_target("My Note.md") == "My Note.md"

    def test_strips_display_text(self) -> None:
        """Test display text after pipe is removed."""
        assert normalize_link_target("note|Display Text") == "note.md"

    def test_strips_anchor(self) -> None:
        """Test anchor is removed."""
        assert normalize_link_target("note#section") == "note.md"

    def test_handles_both_pipe_and_anchor(self) -> None:
        """Test both pipe and anchor are handled."""
        assert normalize_link_target("note#section|text") == "note.md"

    def test_normalizes_backslashes(self) -> None:
        """Test backslashes are normalized to forward slashes."""
        assert normalize_link_target("folder\\note") == "folder/note.md"

    def test_strips_whitespace(self) -> None:
        """Test leading/trailing whitespace is stripped."""
        assert normalize_link_target("  My Note  ") == "My Note.md"
