# Data Pipeline

End-to-end extraction flow, exercise matching, AI classification, and three-tier save model.

## Extraction Flow

```
Markdown Note → Hash Check (skip if unchanged) → Load Schema → Claude Tool-Use Call
    → Parse Response → Upsert into DB → Log to extraction_log
```

### Detailed Steps

1. **File written** to vault (via editor save, quick capture, or import)
2. **Hash check** — compare file content hash with `extraction_log`; skip if unchanged
3. **Load schemas** from `shared/schemas/` (daily_metrics, exercise_log, food_log, daily_tasks)
4. **Claude API call** (Haiku 4.5) — tool-use structured extraction with schemas as tools
5. **Parse response** — extract tool call results into typed objects
6. **Validate** — check dates, IDs, required fields
7. **Upsert** into DuckDB/Postgres tables
8. **Log** extraction result to `extraction_log` table
9. **Auto-label** new exercises — call `label_new_exercises()` to classify any unknown exercise names

### ID Formats

- Activity: `{YYYYMMDD}_{type}_{index}` (e.g., `20260115_str_1`)
- Exercise: `{activity_id}_{exercise_name}_{set_number}` (e.g., `20260115_str_1_squat_1`)
- Task: `{YYYYMMDD}_{8-char-hex}` (e.g., `20260115_a1b2c3d4`)

### Validation Rules

1. Dates must be valid and match the note's date
2. Exercise names normalized to snake_case
3. Numeric values must be positive
4. Required fields cannot be null
5. Each set is a separate row in exercise_log

## Three-Tier Save Model

Prevents excessive Claude API calls from autosave.

### Tier 1: Autosave (every 60 seconds)
- Save markdown to disk only — **no Claude extraction**
- Timer resets on each keystroke (debounced)
- Backend: `/vault/file` with `extract: false`

### Tier 2: Explicit Save (Cmd+S)
- Save to disk **AND** trigger Claude extraction
- User's explicit signal that content is ready
- Backend: `/vault/file` with `extract: true` (default)

### Tier 3: Navigation Trigger
- Extract on tab switch or file close (if unsaved changes exist)
- Uses `isDirty` flag in editor state

### Save State Indicators

| State | Display | Color |
|-------|---------|-------|
| Clean | "Saved" | Muted gray |
| Dirty | "Unsaved changes" | Amber |
| Saving | "Saving..." | Teal |
| Extracting | "Extracting data..." | Teal + spinner |
| Extracted | "Saved & extracted" | Green (fades 3s) |
| Error | "Save failed" | Rose |

## Exercise Matching

Multi-tier system in `ExerciseMatcher` (`backend/src/extraction/exercise_matcher.py`):

### Matching Tiers (in order)

1. **Built-in definitions** — 330+ exercises from `shared/exercise_definitions.json` with aliases, muscle groups, category, recovery hours
2. **AI exercise cache** — Claude-generated mappings stored in `data/ai_exercise_cache.json` (local) or `user_settings` (cloud)
3. **Community exercises** — User-contributed exercises in `community_exercises` table
4. **Claude classification** — For truly unknown exercises, call Claude to classify with muscle groups

### ExerciseMatcher Public Methods

- `match(name)` → canonical exercise key
- `get_muscle_groups(key)` → list of muscle groups
- `get_metadata(key)` → full exercise metadata (category, recovery_hours, etc.)

### Auto-Classification Pipeline

1. After extraction, scan for exercise names not in built-in definitions
2. Check AI cache for existing mapping
3. If unknown, batch-call `label_new_exercises()` (Claude Haiku 4.5)
4. Claude returns: canonical name, muscle groups, category, recovery hours
5. Store results in AI cache and community exercises table
6. On manual exercise contribution via `/exercises`, auto-fill muscle groups via Claude

## Exercise Definitions Structure

```json
{
  "exercise_key": {
    "display": "Display Name",
    "aliases": ["alias1", "alias2"],
    "muscle_groups": ["chest", "triceps", "shoulders"],
    "category": "compound|isolation|cardio|flexibility",
    "recovery_hours": 48
  }
}
```

## Task Two-Way Sync

When a personal task status changes in the kanban UI:

1. **Kanban → Markdown:** Update checkbox in source daily note
   - `backlog` → `- [ ] description`
   - `done` → `- [x] description`
   - `cancelled` → `- [-] description`

2. **Markdown → DuckDB:** When note is saved + extracted, Claude reads checkboxes and updates task status

## Data Portability

- `GET /export/json` — Export all extracted data as JSON
- `GET /export/csv` — Export as CSV files
- `POST /import/json` — Import JSON data back into the system
