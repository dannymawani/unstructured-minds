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

### Exercise Log
- `activity_id` (VARCHAR): Format `{YYYYMMDD}_{type}_{index}`
- `date` (DATE): Exercise date
- `activity_type` (VARCHAR): str, bjj, run, rec
- `exercise_name` (VARCHAR)
- `sets`, `reps`, `weight_kg` (NUMERIC)
- `duration_min` (INTEGER)
- `notes` (VARCHAR)

### Food Log
- `date` (DATE)
- `meal_type` (VARCHAR): breakfast, lunch, dinner, snack
- `food_item` (VARCHAR)
- `calories`, `protein_g`, `carbs_g`, `fat_g` (NUMERIC)

### Daily Metrics
- `date` (DATE)
- `weight_kg`, `sleep_hours`, `energy_level`, `mood_score` (NUMERIC)

### Daily Tasks
- `date` (DATE)
- `task` (VARCHAR)
- `status` (VARCHAR): done, pending, moved
- `priority` (VARCHAR): high, medium, low

## Query Examples

```sql
-- Weekly exercise summary
SELECT
  DATE_TRUNC('week', date) as week,
  activity_type,
  COUNT(*) as sessions,
  SUM(duration_min) as total_minutes
FROM exercise_log
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
