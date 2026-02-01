# 04 - Data Layer Specification

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Markdown     │────▶│   Extraction    │────▶│     DuckDB      │
│     Notes       │     │    (Claude)     │     │    Database     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        ▼                                               ▼
   Human-readable                               SQL-queryable
   Version-controlled                           Dashboards
   Portable                                     Analytics
```

---

## Directory Structure

```
vault/                          # User's markdown notes (volume mount)
├── Daily-Notes/
│   └── 2026-01/
│       ├── 2026-01-31.md
│       └── ...
├── Training/
├── Work/
└── ...

data/                           # App data (volume mount)
├── unstructured.duckdb         # Main database (single file)
├── exercise_log.csv            # Flat CSV files
├── food_log.csv
├── daily_metrics.csv
├── daily_tasks.csv
└── schemas/
    └── *.json

config/                         # Configuration (volume mount)
├── settings.json
└── cache/                      # LLM response cache
```

---

## DuckDB Schema

```sql
-- Activities (workouts, sessions)
CREATE TABLE activities (
    id VARCHAR PRIMARY KEY,           -- '20260131_str_1'
    date DATE NOT NULL,
    activity_type VARCHAR NOT NULL,   -- 'strength', 'bjj', 'run', etc.
    duration_minutes INTEGER,
    notes VARCHAR,
    source_file VARCHAR,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exercise log (from workout tracking)
CREATE TABLE exercise_log (
    id VARCHAR PRIMARY KEY,           -- '20260131_str_1_squat_1'
    activity_id VARCHAR NOT NULL,     -- '20260131_str_1'
    date DATE NOT NULL,
    exercise_name VARCHAR NOT NULL,
    weight_kg DECIMAL(5,1),
    reps INTEGER,
    set_number INTEGER,
    duration_minutes INTEGER,
    distance_km DECIMAL(5,2),
    notes VARCHAR,
    source_file VARCHAR,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily metrics (mood, sleep, etc.)
CREATE TABLE daily_metrics (
    date DATE PRIMARY KEY,
    sleep_hours DECIMAL(3,1),
    sleep_quality INTEGER,            -- 1-5 scale
    energy INTEGER,                   -- 1-5 scale
    mood INTEGER,                     -- 1-5 scale
    stress INTEGER,                   -- 1-5 scale
    notes VARCHAR,
    source_file VARCHAR,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Food log
CREATE TABLE food_log (
    id VARCHAR PRIMARY KEY,
    date DATE NOT NULL,
    meal_type VARCHAR,                -- 'breakfast', 'lunch', 'dinner', 'snack'
    time TIME,
    description VARCHAR,
    calories INTEGER,
    protein_g INTEGER,
    carbs_g INTEGER,
    fat_g INTEGER,
    notes VARCHAR,
    source_file VARCHAR,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks (from daily notes)
CREATE TABLE tasks (
    id VARCHAR PRIMARY KEY,
    date DATE NOT NULL,
    description VARCHAR NOT NULL,
    status VARCHAR,                   -- 'pending', 'completed', 'cancelled'
    completed_at TIMESTAMP,
    category VARCHAR,
    priority INTEGER,
    source_file VARCHAR,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Extraction metadata (track what's been processed)
CREATE TABLE extraction_log (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR NOT NULL,
    file_hash VARCHAR NOT NULL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN,
    error_message VARCHAR
);
```

---

## ID Generation

**Composite key pattern** - deterministic, human-readable, idempotent:

| Table | Format | Example |
|-------|--------|---------|
| activities | `{YYYYMMDD}_{type}_{index}` | `20260131_str_1` |
| exercise_log | `{activity_id}_{exercise}_{set}` | `20260131_str_1_squat_1` |

Exercise names normalized to snake_case (e.g., `leg_press` not `leg press`).

---

## Extraction Pipeline

```
File Save Detected
        │
        ▼
Check extraction_log for file_hash
        │
        ├── Match → Skip (no changes)
        │
        └── No match → Continue
                │
                ▼
        Parse markdown sections
                │
                ▼
        Send to Claude for extraction (tool use)
                │
                ▼
        Validate response JSON
                │
                ▼
        Delete old records for this source_file
                │
                ▼
        Insert new records into DuckDB
                │
                ▼
        Update extraction_log with new hash
```

---

## Query Examples

```sql
-- Weekly Training Summary
SELECT activity_type, COUNT(*) as sessions, SUM(duration_minutes) as total_minutes
FROM activities
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY activity_type;

-- Exercise Progress
SELECT date, weight_kg, reps, ROUND(weight_kg * (1 + reps / 30.0), 1) as estimated_1rm
FROM exercise_log
WHERE exercise_name = 'squat'
ORDER BY date;

-- Task Completion Rate
SELECT DATE_TRUNC('week', date) as week,
       COUNT(*) FILTER (WHERE status = 'completed') as completed,
       COUNT(*) as total
FROM tasks
GROUP BY week;
```

---

*Next: [05-LLM-INTEGRATION.md](./05-LLM-INTEGRATION.md)*
