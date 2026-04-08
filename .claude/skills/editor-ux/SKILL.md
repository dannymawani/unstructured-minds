---
name: editor-ux
description: Documents editor UX improvements including template discoverability, WYSIWYG toolbar, autosave behavior, and raw markdown toggle. Reference when working on the Milkdown editor or note creation flow.
user-invocable: false
---

# Editor UX Improvements

## Overview

Improve the note editing experience to make template selection easy, provide WYSIWYG formatting tools, and add reliable autosave without triggering unnecessary Claude calls.

## 1. Template Discoverability

### Current Problem
Templates exist in `vault/Templates/` but there is no easy way to discover or select them from the editor.

### Solution

**Sidebar "New Note" Dropdown:**
- Replace simple "New Note" button with a dropdown/split button
- Options: "Blank Note", then each template by name (Daily Note, Strength Training, Meeting, Project, Code Snippet)
- Template list reads from `vault/Templates/` directory dynamically

**Quick Daily Note Button:**
- Dedicated prominent button: "Today's Note" or icon with calendar + plus
- One-click creates today's daily note from daily template
- If today's note already exists, opens it instead
- Keyboard shortcut: `Ctrl+D` / `Cmd+D`

**Template Selection in New Note Dialog:**
- When creating a new note, show a card grid of available templates
- Each card shows: template name, brief description, preview of sections
- Click to create new note from that template
- "Blank" option always available

### Template Preview
- Hovering a template card shows a preview of the template structure
- Preview renders the markdown sections as a skeleton/outline

## 2. WYSIWYG Toolbar

### Milkdown Plugins

Use the Milkdown plugin ecosystem for rich editing:

**@milkdown/plugin-toolbar (or custom toolbar):**
- Floating toolbar appears on text selection
- Buttons: Bold, Italic, Strikethrough, Code, Link
- Block-level: H1, H2, H3, Bullet List, Numbered List, Checkbox, Quote, Code Block, Divider

**@milkdown/plugin-slash:**
- Type `/` at start of line to open command palette
- Commands: Heading 1-3, Bullet List, Numbered List, Task List, Code Block, Quote, Divider, Table
- Filter by typing (e.g., `/head` shows heading options)

**@milkdown/plugin-block:**
- Drag handle on the left of each block
- Click to open block-level menu (change block type, delete, duplicate)

### Toolbar Layout

```
┌─────────────────────────────────────────────────────┐
│ B  I  S  ~  </>  🔗  │  H1 H2 H3  │  • 1. ☐  │  "" {} ─ │
└─────────────────────────────────────────────────────┘
```

- First group: Inline formatting
- Second group: Headings
- Third group: Lists (bullet, numbered, checkbox)
- Fourth group: Block elements (quote, code block, divider)

## 3. Autosave Behavior

See the `performance-optimization` skill for the full three-tier save model. Summary:

- **60-second autosave**: Saves to disk only, no Claude extraction
- **Cmd+S**: Saves to disk AND extracts
- **Tab switch**: Saves + extracts if there are unsaved changes

### Save State Indicator

Show a small indicator in the editor toolbar or status bar:
- "Saved" (muted) — no unsaved changes
- "Unsaved changes" (amber dot) — changes pending
- "Saving..." (teal spinner) — disk save in progress
- "Extracting..." (teal spinner) — Claude extraction in progress
- "Saved & extracted" (green check) — fades after 3 seconds

## 4. Raw Markdown Toggle

### Implementation
- Toggle button in the editor toolbar: `</>` icon
- **WYSIWYG mode** (default): Full Milkdown rendering with toolbar
- **Raw mode**: Plain textarea/code editor showing raw markdown
- Content syncs between modes on toggle
- Keyboard shortcut: `Ctrl+Shift+M` / `Cmd+Shift+M`

### Raw Mode Features
- Monospace font (JetBrains Mono)
- Line numbers
- Basic syntax highlighting for markdown
- No toolbar (raw editing)
- Same autosave behavior

## 5. Editor Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+S` | Save + extract |
| `Cmd+D` | Quick daily note |
| `Cmd+Shift+M` | Toggle raw/WYSIWYG |
| `Cmd+B` | Bold |
| `Cmd+I` | Italic |
| `Cmd+K` | Insert link |
| `Cmd+Shift+C` | Insert code block |
| `Cmd+Shift+L` | Toggle bullet list |
| `Cmd+Shift+O` | Toggle numbered list |
| `Cmd+Shift+T` | Toggle task list |

## Implementation Priority

1. **Autosave** — Critical for data safety
2. **Template selection UX** — High impact on daily usage
3. **WYSIWYG toolbar** — Medium, improves editing comfort
4. **Raw markdown toggle** — Nice to have
