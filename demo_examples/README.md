# Demo Examples

This folder contains reference examples showing how data extraction should work in Unstructured Minds.

## Structure

```
demo_examples/
├── input_notes/           # Sample markdown notes (user input)
├── expected_output/       # CSV files showing expected extraction results
│   ├── activities.csv     # Flat file - all activities
│   ├── exercise_log.csv   # Flat file - all exercises
│   ├── food_log.csv       # Flat file - all meals
│   ├── daily_metrics.csv  # Flat file - all daily metrics
│   └── tasks.csv          # Flat file - all tasks
└── schemas/               # JSON schema definitions
```

## Storage Design

**Flat CSV files** - one file per data type containing all records. DuckDB filters by date column.

This is simpler than date-partitioned folders and efficient for personal data volumes (~10K rows).

## How to Use

1. **Input Notes**: Natural language markdown that users write
2. **Expected Output**: The CSV data Claude should extract
3. **Schemas**: Defines column names, types, and allowed values

## Examples Included

| Example | Input Note | Extracted Data |
|---------|------------|----------------|
| Workout day | `2026-01-15.md` | activities, exercise_log, daily_metrics |
| Food logging | `2026-01-16.md` | food_log, daily_metrics |
| Mixed day | `2026-01-17.md` | All data types |

## Key Patterns

### Table Design

**Normalized** - `activities` and `exercise_log` are separate tables:
- `activities`: One row per workout session (e.g., `20260115_str_1`)
- `exercise_log`: One row per set, references activity via `activity_id`

### ID Generation

Composite keys for deterministic, idempotent extraction:

| Table | ID Format | Example |
|-------|-----------|---------|
| activities | `{date}_{activity_type}_{index}` | `20260115_str_1` |
| exercise_log | `{activity_id}_{exercise_name}_{set_number}` | `20260115_str_1_squat_1` |
| food_log | `{date}_{meal_type}_{index}` | `20260115_breakfast_1` |
| tasks | `{date}_{hash}` | `20260115_abc123` |
| daily_metrics | `{date}` (primary key) | `2026-01-15` |

### Column Naming

Uses descriptive names:
- `set_number` (not `sets`)
- `duration_minutes` (not `duration_min`)
- `description` (not `task` or `food`)

### Extraction Rules

1. Each workout set is logged as a **separate row** in exercise_log
2. Activity IDs link all exercises in a session: `YYYYMMDD_activity_type_index`
3. Food entries are split by meal type (breakfast, lunch, dinner, snack)
4. Daily metrics capture sleep, energy, mood ratings (1-10 scale)
5. Tasks have status: pending, completed, cancelled
6. Exercise names use snake_case: `leg_press`, `romanian_deadlift`
