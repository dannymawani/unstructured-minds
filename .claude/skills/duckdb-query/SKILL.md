---
name: duckdb-query
description: Query the DuckDB database for data analysis and insights. Use when exploring structured data extracted from notes.
allowed-tools: Bash(duckdb *), Read
---

# DuckDB Query Assistant

Query the project's DuckDB database for data analysis.

## Database Location

The database is at `.unstructured/unstructured.duckdb` (relative to vault root).

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
- `food_item` (VARCHAR)
- `calories`, `protein_g`, `carbs_g`, `fat_g` (NUMERIC)

### Daily Metrics
- `date` (DATE): Primary key
- `sleep_hours` (DECIMAL)
- `sleep_quality` (INTEGER): 1-5 scale
- `energy` (INTEGER): 1-5 scale
- `mood` (INTEGER): 1-5 scale
- `stress` (INTEGER): 1-5 scale
- `notes` (VARCHAR)
- `source_file` (VARCHAR)

### Tasks
- `id` (VARCHAR): Primary key
- `date` (DATE)
- `description` (VARCHAR): Task description
- `status` (VARCHAR): pending, completed, cancelled
- `completed_at` (TIMESTAMP)
- `category` (VARCHAR)
- `priority` (INTEGER): 1-3
- `source_file` (VARCHAR)

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
```

## Execution

1. Parse the user's question: $ARGUMENTS
2. Identify relevant tables
3. Write an efficient SQL query
4. Execute with `duckdb .unstructured/unstructured.duckdb -c "QUERY"`
5. Present results in a readable format
6. Provide insights from the data

## Arguments

$ARGUMENTS
