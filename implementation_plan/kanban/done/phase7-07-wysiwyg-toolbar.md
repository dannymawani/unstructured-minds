# Add WYSIWYG Toolbar

**Phase:** 7 - Editor UX
**Priority:** Medium
**Status:** Done
**Completed:** 2026-02-06
**Branch:** feature/editor-ux

## Description

Add a Milkdown toolbar with inline formatting (bold, italic, strikethrough, code, link), block-level controls (headings, lists, quote, code block), and slash command palette.

## Tasks

- [x] Use @milkdown/kit/plugin/slash (bundled in kit)
- [x] Slash menu: H1-H3, bullet list, numbered list, quote, code block, divider
- [x] Floating toolbar on text selection: Bold, Italic, Strikethrough, Inline Code
- [x] Styled with popover/accent classes matching project design
- [x] EditorPlugins.tsx created as self-contained module

## Acceptance Criteria

- Slash commands work when typing / at start of line
- Floating toolbar appears on text selection
- All formatting options work correctly
- Raw markdown toggle switches between WYSIWYG and plaintext
- Toolbar styled consistently with brand
