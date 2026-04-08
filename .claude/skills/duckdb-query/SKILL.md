---
name: duckdb-query
description: Query the DuckDB database for data analysis and insights. Use when exploring structured data extracted from notes.
allowed-tools: Bash(duckdb *), Read
---

# DuckDB Query Assistant

Query the project's DuckDB database for data analysis.

## Database Location

The database is at `data/unstructured.duckdb` (relative to project root).

## Common Schemas

Based on the project's data extraction patterns:

### Activities
- `id` (VARCHAR): Format `{YYYYMMDD}_{type}_{index}` (e.g., `20260131_str_1`)
- `date` (DATE): Activity date
- `activity_type` (VARCHAR): str, bjj, run, rec
- `duration_minutes` (INTEGER)
- `notes` (VARCHAR)
- `source_file` (VARCHAR)

### Exercise Log
- `id` (VARCHAR): Format `{activity_id}_{exercise_name}_{set_number}` (e.g., `20260131_str_1_squat_1`)
- `activity_id` (VARCHAR): Foreign key to activities
- `date` (DATE): Exercise date
- `exercise_name` (VARCHAR): Exercise name (snake_case)
- `weight_kg` (DECIMAL)
- `reps` (INTEGER)
- `set_number` (INTEGER)
- `duration_minutes` (INTEGER): For timed exercises
- `distance_km` (DECIMAL): For cardio
- `notes` (VARCHAR)

### Food Log
- `date` (DATE)
- `meal_type` (VARCHAR): breakfast, lunch, dinner, snack
- `description` (VARCHAR)
- `calories`, `protein_g`, `carbs_g`, `fat_g` (NUMERIC)

### Daily Metrics
- `date` (DATE): Primary key
- `sleep_hours` (DECIMAL)
- `sleep_quality` (INTEGER): 1-10 scale
- `energy` (INTEGER): 1-10 scale
- `mood` (INTEGER): 1-10 scale
- `stress` (INTEGER): 1-10 scale
- `notes` (VARCHAR)
- `source_file` (VARCHAR)

### Personal Tasks (`tasks`)
- `id` (VARCHAR): Primary key, format `{YYYYMMDD}_{8-char-hex}` (e.g., `20260207_a1b2c3d4`)
- `date` (DATE): Task creation date
- `description` (VARCHAR): Task text
- `status` (VARCHAR): `backlog`, `in_progress`, `done`, `cancelled`
- `completed_at` (TIMESTAMP): Auto-set when status becomes `done` or `cancelled`
- `category` (VARCHAR): `work`, `personal`, `training`, or `other`
- `priority` (INTEGER): 1-3
- `source_file` (VARCHAR): Path to source markdown file (e.g., `Daily-Notes/2026-02/2026-02-07.md`)
- `deadline` (DATE): Optional deadline
- `extracted_at` (TIMESTAMP): Auto-set on insert

**Status migrations on startup:** `pending`/`todo` -> `backlog`, `completed` -> `done`, `rolled_over` -> `in_progress`

**Two-way sync:** Updating a task's status or description via API also updates the checkbox in the source markdown file.

### Dev Kanban Tasks (`kanban_tasks`)
- `id` (VARCHAR): Primary key, derived from title (lowercase, hyphens, max 60 chars)
- `title` (VARCHAR): Task title
- `phase` (VARCHAR): Development phase (optional, filterable)
- `priority` (VARCHAR): Priority label (optional)
- `status` (VARCHAR): `not_started`, `in_progress`, `done`
- `branch` (VARCHAR): Git branch name
- `depends_on` (VARCHAR): ID of blocking task
- `description` (VARCHAR): Short description
- `content` (TEXT): Extended content / acceptance criteria
- `deadline` (DATE): Optional deadline
- `created_at` (TIMESTAMP): Auto-set on insert
- `completed_at` (TIMESTAMP): Auto-set when moved to `done`

### Kanban Task Updates (`kanban_task_updates`)
- `id` (INTEGER): Primary key (auto-incrementing)
- `task_id` (VARCHAR): Foreign key to `kanban_tasks.id`
- `note` (TEXT): Status update or note
- `created_at` (TIMESTAMP): Auto-set on insert

**Cascade delete:** Deleting a kanban task also deletes its updates.

## Query Examples

```sql
-- Weekly activity summary
SELECT
  DATE_TRUNC('week', date) as week,
  activity_type,
  COUNT(*) as sessions,
  SUM(duration_minutes) as total_minutes
FROM activities
GROUP BY 1, 2
ORDER BY 1 DESC;

-- Daily calorie intake
SELECT date, SUM(calories) as total_calories
FROM food_log
GROUP BY date
ORDER BY date DESC
LIMIT 7;

-- Active personal tasks (not done/cancelled)
SELECT id, date, description, status, category, priority
FROM tasks
WHERE status IN ('backlog', 'in_progress')
ORDER BY priority ASC, date DESC;

-- Task completion rate by category
SELECT
  category,
  COUNT(*) FILTER (WHERE status = 'done') as completed,
  COUNT(*) as total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'done') / COUNT(*), 1) as pct
FROM tasks
GROUP BY category;

-- Dev kanban board overview
SELECT status, COUNT(*) as count
FROM kanban_tasks
GROUP BY status;

-- Kanban tasks with recent updates
SELECT kt.id, kt.title, kt.status, ktu.note, ktu.created_at
FROM kanban_tasks kt
LEFT JOIN kanban_task_updates ktu ON kt.id = ktu.task_id
ORDER BY ktu.created_at DESC
LIMIT 10;
```

## Modification Examples

```sql
-- Delete all personal tasks
DELETE FROM tasks;

-- Delete all kanban tasks (delete updates first)
DELETE FROM kanban_task_updates;
DELETE FROM kanban_tasks;

-- Move a kanban task to done
UPDATE kanban_tasks SET status = 'done', completed_at = NOW() WHERE id = 'my-task-id';

-- Mark a personal task as done
UPDATE tasks SET status = 'done', completed_at = NOW() WHERE id = '20260207_a1b2c3d4';

-- Bulk cancel old backlog tasks
UPDATE tasks SET status = 'cancelled', completed_at = NOW()
WHERE status = 'backlog' AND date < '2025-01-01';
```

## Execution

1. Parse the user's question: $ARGUMENTS
2. Identify relevant tables
3. Write an efficient SQL query
4. Execute with `duckdb data/unstructured.duckdb -c "QUERY"`
5. Present results in a readable format
6. Provide insights from the data

## Arguments

$ARGUMENTS
