---
name: performance-optimization
description: Documents the three-tier save model to prevent excessive Claude API calls. Reference when modifying file saving, extraction triggers, or editor autosave behavior.
user-invocable: false
---

# Performance Optimization — Extraction Timing

## Problem

The current implementation triggers Claude extraction on every keystroke (via file watcher detecting file changes). This causes:
- Excessive API calls and cost
- Poor UX with constant processing indicators
- Race conditions when extraction overlaps with typing

## Solution: Three-Tier Save Model

### Tier 1: Autosave (every 60 seconds)

**Action:** Save markdown to disk only. No Claude extraction.

- `MarkdownEditor.tsx` sets a 60-second interval timer
- On timer fire: POST to `/vault/files/{path}` with `extract: false` query param
- Save indicator shows "Saved" briefly, then fades
- Timer resets on each keystroke (debounced)
- Timer clears on unmount or file switch

**Backend change:** Add `extract: bool = True` query parameter to the file write endpoint. When `false`, write to disk and return immediately — skip extraction pipeline.

### Tier 2: Explicit Save (Cmd+S / Ctrl+S)

**Action:** Save to disk AND trigger Claude extraction.

- `MarkdownEditor.tsx` listens for Cmd+S / Ctrl+S keyboard shortcut
- Calls the same endpoint with `extract: true` (default)
- Save indicator shows "Saving & extracting..." then "Extracted"
- This is the user's explicit signal that content is ready for extraction

### Tier 3: Navigation Trigger

**Action:** Extract on tab switch or file close (if unsaved changes exist).

- `App.tsx` detects when user switches away from editor tab (to Data, Insights, Kanban)
- If there are unsaved changes, save + extract before navigation completes
- Also triggers on file browser selection change (switching to different file)
- Uses a `isDirty` flag in editor state to track unsaved changes

## Implementation Changes

### FileWriteRequest Model (backend)

```python
# Add extract parameter to the file write endpoint
@router.put("/vault/files/{file_path:path}")
async def write_file(
    file_path: str,
    request: FileWriteRequest,
    extract: bool = Query(True, description="Whether to trigger Claude extraction after save"),
):
    # Write file to disk
    await vault_service.write_file(file_path, request.content)

    # Only extract if requested
    if extract:
        await extraction_service.extract(file_path, request.content)

    return {"status": "ok", "extracted": extract}
```

### MarkdownEditor.tsx

```typescript
// Add autosave timer
const AUTOSAVE_INTERVAL_MS = 60_000;
const autosaveTimer = useRef<NodeJS.Timeout | null>(null);
const isDirty = useRef(false);

// Reset timer on content change
const handleContentChange = (content: string) => {
  isDirty.current = true;
  if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
  autosaveTimer.current = setTimeout(() => {
    saveFile(content, { extract: false }); // Tier 1: disk only
    isDirty.current = false;
  }, AUTOSAVE_INTERVAL_MS);
};

// Cmd+S handler
const handleKeyDown = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') {
    e.preventDefault();
    saveFile(currentContent, { extract: true }); // Tier 2: disk + extract
    isDirty.current = false;
  }
};
```

### App.tsx — Navigation Trigger

```typescript
// Before tab switch, save + extract if dirty
const handleTabChange = async (newTab: string) => {
  if (isDirty && activeTab === 'editor') {
    await saveFile(currentContent, { extract: true }); // Tier 3
  }
  setActiveTab(newTab);
};
```

### file_watcher.py

**Remove or disable** the automatic extraction trigger from the file watcher. The watcher should still detect changes for the file browser (refresh file list), but should NOT trigger extraction. Extraction is now controlled entirely by the frontend via the `extract` parameter.

## Save State Indicator

The editor should show a persistent save state indicator:

| State | Display | Color |
|-------|---------|-------|
| Clean | "Saved" | Muted gray |
| Dirty (unsaved) | "Unsaved changes" | Amber |
| Saving (disk only) | "Saving..." | Teal |
| Extracting | "Extracting data..." | Teal with spinner |
| Extracted | "Saved & extracted" | Green, fades after 3s |
| Error | "Save failed" | Rose |

## Performance Targets

- Autosave should complete in < 100ms (disk write only)
- Explicit save + extraction should complete in < 5s
- Navigation trigger should not block tab switch for more than 5s
- Zero Claude API calls from autosave
