# 60-Second Autosave

**Phase:** 7 - Editor UX
**Priority:** High
**Status:** Done
**Completed:** 2026-02-06
**Branch:** feature/editor-ux
**Depends On:** phase7-05

## Description

Implement 60-second autosave that saves markdown to disk without triggering Claude extraction. Include save state indicator showing current status (saved, unsaved, saving, extracting).

## Tasks

- [x] Add 60-second interval autosave timer to MarkdownEditor
- [x] Autosave calls POST /vault/file?extract=false
- [x] Save state indicator in header (saving/extracting/saved)
- [x] Timer clears on unmount, content flushed on file switch
- [x] Update editor tests

## Acceptance Criteria

- Autosave fires every 60s of inactivity
- Autosave does NOT trigger Claude extraction
- Save state indicator accurately reflects current state
- Timer properly cleaned up on unmount
- No data loss on file switch
