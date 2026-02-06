# Fix Extraction Timing

**Phase:** 7 - Performance
**Priority:** Critical
**Status:** Done
**Completed:** 2026-02-06
**Branch:** feature/extraction-performance

## Description

Implement the three-tier save model: (1) autosave every 60s -> disk only, no Claude; (2) explicit Cmd+S -> disk + extraction; (3) navigation trigger -> extract on tab switch. Add `extract` query param to file write endpoint. Disable file watcher extraction trigger.

## Tasks

- [x] Add `extract: bool = True` query parameter to POST /vault/file
- [x] Update file watcher to NOT trigger extraction (logging only)
- [x] Implement 60-second autosave interval in MarkdownEditor.tsx (extract: false)
- [x] Implement Cmd+S handler for explicit save + extract
- [x] Implement navigation trigger in App.tsx (save+extract on file switch if dirty)
- [x] Add isDirty flag to editor state
- [x] Add save state indicator (saving/extracting/saved in header)
- [x] Update editor tests

## Acceptance Criteria

- Zero Claude API calls from autosave
- Autosave completes in < 100ms (disk only)
- Cmd+S triggers extraction
- Tab switch triggers extraction if content is dirty
- Save state indicator visible and accurate
- File watcher no longer triggers extraction

## Key Files

- `backend/src/api/routes.py`
- `backend/src/watcher/__init__.py`
- `frontend/src/components/MarkdownEditor.tsx`
- `frontend/src/App.tsx`
