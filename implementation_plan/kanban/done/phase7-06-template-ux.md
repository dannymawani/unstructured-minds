# Improve Template Selection UX

**Phase:** 7 - Editor UX
**Priority:** High
**Status:** Done
**Completed:** 2026-02-06
**Branch:** feature/editor-ux

## Description

Replace the simple "New Note" button with a dropdown showing all templates. Add a "Quick Daily Note" button with Ctrl+D shortcut. Show template card grid when creating new notes.

## Tasks

- [x] Replace "New file" button with dropdown (Blank Note, Today's Note, From Template...)
- [x] "Today's Note" button opens/creates daily note via existing createDailyNote
- [x] Cmd+D shortcut already existed
- [x] Add Cmd+T shortcut for template picker
- [x] "From Template..." opens existing TemplatePicker modal (loads from API)
- [x] Update FileTree tests

## Acceptance Criteria

- Dropdown shows all available templates
- "Today's Note" creates daily note in one click
- Ctrl+D shortcut works
- Template preview visible on hover
- Templates loaded dynamically (no hardcoded list)
