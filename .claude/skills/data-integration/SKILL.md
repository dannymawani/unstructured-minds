---
name: data-integration
description: Documents the migration strategy from existing date-partitioned CSVs to flat DuckDB tables. Covers column mapping, template merging, and config file integration. Reference when working on data import or schema changes.
user-invocable: false
---

# Data Integration Guide

## Overview

Migrate existing Obsidian-generated data into the Unstructured Minds DuckDB architecture. The existing data lives in the Obsidian reference repo; the target is DuckDB tables in `data/`.

## Source Data Structure (Obsidian reference repo)

See `/Users/dmh/Code/obsedian` for the original data:
- `data/` — date-partitioned CSVs and schemas
- `secondbrain/Daily-Notes/` — daily note markdown files
- `secondbrain/Templates/` — note templates

## Target Data Structure (data/)

```
data/
├── unstructured.duckdb      # All extracted data in DuckDB tables
├── settings.json            # User preferences
└── schemas/
    ├── exercise_log.json
    ├── food_log.json
    ├── daily_metrics.json
    └── daily_tasks.json
```

## Column Mapping

### exercise_log

The existing schema uses slightly different column names from the new app's extract-data skill. Migration must reconcile both:

| Existing Column | New Column | Notes |
|----------------|------------|-------|
| `date` | `date` | No change |
| `activity_id` | `activity_id` | No change |
| `time` | `time` | Optional, often empty |
| `activity_type` | `activity_type` | No change |
| `exercise` | `exercise_name` | **Rename** |
| `weight_kg` | `weight_kg` | No change |
| `reps` | `reps` | No change |
| `sets` | `set_number` | **Rename + transform**: existing data has one row per set already (no `sets` count column), so add sequential `set_number` per exercise per activity |
| `duration_min` | `duration_minutes` | **Rename** |
| `distance_km` | `distance_km` | No change |
| `notes` | `notes` | No change |

**Important:** The existing CSV already has one row per set (no aggregated sets column). The `sets` column in existing schemas is unused in practice. During migration, compute `set_number` by counting sequential rows of the same exercise within the same `activity_id`.

### food_log, daily_metrics, daily_tasks

These schemas are compatible — columns match between existing and new. Merge by concatenating all date-partitioned files into single flat CSVs.

## Migration Script Requirements

The migration script (`scripts/migrate_existing_data.py`) must:

1. **Scan** source `data/{type}/{year}/{month}/{day}/` for all CSV files
2. **Read** each CSV and validate against its schema
3. **Transform** column names per mapping above
4. **Deduplicate** by primary key (date + activity_id + exercise_name + set_number for exercise_log)
5. **Sort** by date ascending
6. **Write** single flat CSV per data type to `data/`
7. **Copy** schemas to `data/schemas/`, updating column names in the exercise_log schema
9. **Report** summary: rows migrated per type, any validation errors

## Template Merge Strategy

### Existing Templates (6)

| Template | Keep/Merge/Drop |
|----------|----------------|
| `Daily-Note-Template.md` | **Merge** → update `vault/Templates/daily.md` |
| `Strength-Training-Template.md` | **Keep** → copy as `vault/Templates/strength-training.md` |
| `Code-Snippet-Template.md` | **Keep** → copy as `vault/Templates/code-snippet.md` |
| `Project-Template.md` | **Merge** → update `vault/Templates/project.md` |
| `Meeting-Note-Template.md` | **Merge** → update `vault/Templates/meeting.md` |
| `DEFAULT TEMPLATE.md` | **Drop** — generic, replaced by daily template |

### Merge Rules

- Preserve the existing vault template structure (YAML frontmatter with `type` field)
- Incorporate useful sections from existing templates (e.g., the emoji headers from Daily-Note-Template)
- Ensure all templates have proper `type` and `tags` frontmatter for extraction

## Daily Notes Import

- Copy daily notes from the Obsidian reference repo to `vault/Daily-Notes/`
- Maintain the `{YYYY-MM}/{YYYY-MM-DD}.md` structure
- After copy, run extraction on each note to populate DuckDB with historical data
- Expect ~95 daily note files spanning 2024-11 through 2026-01

## Validation

After migration, verify:
1. Row counts match between source (sum of all partitioned files) and target (flat file)
2. No duplicate primary keys
3. All dates are valid and within expected range
4. Column types match schema definitions
5. DuckDB can query the flat CSVs successfully
