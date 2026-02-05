# Keyboard Shortcuts

**Phase:** 2 - Polish
**Priority:** Medium
**Status:** Done

## Description

Implement global keyboard shortcuts for common actions including a command palette.

## Tasks

- [ ] Command palette (Cmd+K)
- [ ] Save file (Cmd+S)
- [ ] New daily note (Cmd+D)
- [ ] Toggle sidebar (Cmd+B)
- [ ] Focus chat (Cmd+/)
- [ ] Quick search (Cmd+P)
- [ ] Shortcut help overlay (Cmd+?)

## Acceptance Criteria

- Cmd+K opens command palette with fuzzy search
- Cmd+S saves current file immediately
- Cmd+D creates/opens today's daily note
- All shortcuts shown in help overlay
- No conflicts with browser/system shortcuts

## Implementation

- Use @tanstack/react-virtual for palette list
- Debounce search input
- Context-aware commands (editor vs file tree)

## Key Files

- `frontend/src/hooks/useKeyboardShortcuts.ts`
- `frontend/src/components/CommandPalette/`
