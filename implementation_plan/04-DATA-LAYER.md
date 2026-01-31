# 04 - Data Layer Design

## Overview

The data layer is the backbone of Unstructured Minds. It bridges unstructured markdown notes and structured, queryable data.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Markdown     │────▶│   Extraction    │────▶│     DuckDB      │
│     Notes       │     │    (Claude)     │     │    Database     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │                                               │
        ▼                                               ▼
   Human-readable                               SQL-queryable
   Version-controlled                           Dashboards
   Portable                                     Analytics
```

---

## Storage Architecture

### Storage Abstraction Layer

All file I/O goes through a `StorageBackend` interface, enabling pluggable storage:

| Backend | Status | Use Case |
|---------|--------|----------|
| **LocalFilesystem** | ✅ v1.0 | Default, fastest, offline |
| **AzureBlobStore** | 🔜 Future | Azure ecosystem |
| **S3Backend** | 🔜 Future | AWS ecosystem |
| **GCPCloudStore** | 🔜 Future | GCP ecosystem |

See [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) for interface details.

### Directory Structure (Docker Volumes)

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
├── unstructured.duckdb         # Main database
├── exercise_log.csv            # Flat CSV files (no date folders)
├── food_log.csv                # DuckDB filters by date column
├── daily_metrics.csv
├── daily_tasks.csv
└── schemas/                    # JSON schemas for extraction
    └── *.json

config/                         # Configuration (volume mount)
├── settings.json
└── cache/                      # LLM response cache
```

> **Simplified:** Flat CSV files instead of date-partitioned folders. DuckDB queries efficiently at personal data volumes (~10K rows).

---

## DuckDB Schema

### Core Tables

```sql
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
    source_file VARCHAR,              -- Path to originating .md file
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

-- Extraction metadata (track what's been processed)
CREATE TABLE extraction_log (
    id INTEGER PRIMARY KEY,
    file_path VARCHAR NOT NULL,
    file_hash VARCHAR NOT NULL,       -- Detect changes
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN,
    error_message VARCHAR
);
```

---

## Why DuckDB?

| Feature | DuckDB | SQLite | PostgreSQL |
|---------|--------|--------|------------|
| Embedded (no server) | ✅ | ✅ | ❌ |
| Analytical queries | ★★★★★ | ★★☆☆☆ | ★★★★☆ |
| Column-oriented | ✅ | ❌ | ❌ |
| CSV import/export | Native | Needs extension | COPY command |
| JSON support | ✅ | Basic | ✅ |
| Window functions | Full | Full | Full |
| Parquet support | Native | ❌ | Extension |
| Bundle size | ~20MB | ~1MB | N/A |
| Query performance | Excellent | Good | Excellent |

**Why DuckDB wins for this use case:**
1. Excellent for analytical queries (aggregations, time series)
2. Native CSV/Parquet import (can query CSVs directly)
3. Single file, embedded (no server to manage)
4. Modern SQL features (window functions, CTEs)
5. Fast enough for personal data volumes

---

## Extraction Pipeline

### On File Save

```
┌─────────────────────────────────────────────────────────────────┐
│                    File Save Detected                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Check extraction_log for file_hash                          │
│     - If unchanged, skip extraction                             │
│     - If new/changed, continue                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Parse markdown structure                                     │
│     - Extract known sections (## Workout, ## Tasks, etc.)       │
│     - Identify tables, lists, metadata                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Send to Claude for extraction                                │
│     - Structured prompt with expected schema                    │
│     - Return JSON matching table schemas                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Validate extracted data                                      │
│     - Type checking                                              │
│     - Required fields                                           │
│     - Referential integrity                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Upsert to DuckDB                                            │
│     - Delete old records from this source_file                  │
│     - Insert new records                                        │
│     - Update extraction_log                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Claude Extraction Prompt

```
You are a data extraction assistant. Extract structured data from this markdown note.

## Source File
{file_path}

## Note Content
{markdown_content}

## Extraction Schema

Return JSON matching these schemas:

### exercise_log
Extract any workout/exercise information:
{
  "exercise_log": [
    {
      "activity_id": "YYYYMMDD_activity_type_index",
      "date": "YYYY-MM-DD",
      "exercise_name": "exercise name",
      "weight_kg": number or null,
      "reps": number or null,
      "set_number": number,
      "duration_minutes": number or null,
      "distance_km": number or null,
      "notes": "string or null"
    }
  ]
}

### daily_metrics
Extract any mood/sleep/energy ratings:
{
  "daily_metrics": {
    "date": "YYYY-MM-DD",
    "sleep_hours": number or null,
    "sleep_quality": 1-5 or null,
    "energy": 1-5 or null,
    "mood": 1-5 or null,
    "stress": 1-5 or null,
    "notes": "string or null"
  }
}

### food_log
Extract any meals mentioned:
{
  "food_log": [
    {
      "date": "YYYY-MM-DD",
      "meal_type": "breakfast|lunch|dinner|snack",
      "time": "HH:MM or null",
      "description": "what was eaten",
      "calories": number or null,
      "protein_g": number or null,
      "carbs_g": number or null,
      "fat_g": number or null
    }
  ]
}

### tasks
Extract task items:
{
  "tasks": [
    {
      "date": "YYYY-MM-DD",
      "description": "task text",
      "status": "pending|completed|cancelled",
      "category": "category or null",
      "priority": 1-3 or null
    }
  ]
}

## Rules
- Only extract information that is clearly present
- Use null for missing values, don't guess
- Dates should be inferred from filename if not in content
- Return empty arrays for categories with no data
```

---

## Query Examples

### Weekly Training Summary

```sql
SELECT
    activity_type,
    COUNT(*) as sessions,
    SUM(duration_minutes) as total_minutes,
    ROUND(AVG(duration_minutes), 0) as avg_duration
FROM activities
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY activity_type
ORDER BY sessions DESC;
```

### Exercise Progress (1RM Estimates)

```sql
SELECT
    exercise_name,
    date,
    weight_kg,
    reps,
    ROUND(weight_kg * (1 + reps / 30.0), 1) as estimated_1rm
FROM exercise_log
WHERE exercise_name = 'squat'
  AND date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY date;
```

### Daily Metrics Trends

```sql
SELECT
    date,
    sleep_hours,
    energy,
    mood,
    AVG(energy) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as energy_7d_avg
FROM daily_metrics
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date;
```

### Task Completion Rate

```sql
SELECT
    DATE_TRUNC('week', date) as week,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / COUNT(*), 1) as completion_pct
FROM tasks
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('week', date)
ORDER BY week;
```

---

## CSV Export (Optional)

For portability/backup, export tables to CSV:

```sql
COPY exercise_log TO 'data/exercise_log.csv' (HEADER, DELIMITER ',');
COPY daily_metrics TO 'data/daily_metrics.csv' (HEADER, DELIMITER ',');
COPY food_log TO 'data/food_log.csv' (HEADER, DELIMITER ',');
COPY tasks TO 'data/tasks.csv' (HEADER, DELIMITER ',');
```

Or query CSVs directly without import:

```sql
SELECT * FROM read_csv_auto('data/exercise_log/*.csv');
```

---

## Migration from Current System

### Current State
- CSVs in `data/` with nested date folders
- Python scripts for extraction
- No central database

### Migration Steps

1. Create DuckDB schema
2. Import existing CSVs:
   ```sql
   INSERT INTO exercise_log
   SELECT * FROM read_csv_auto('data/exercise_log/**/*.csv');
   ```
3. Add `source_file` to track origins
4. Run extraction on all existing notes to populate `extraction_log`

---

## Resolved Design Decisions

### Extraction Timing
**Decision:** Real-time extraction on save with debounce (2 seconds after last edit).
- Extraction triggers automatically when a file is saved
- Debouncing prevents excessive API calls during rapid edits
- Batch processing available on app startup for changed files

### Conflict Resolution
**Decision:** Markdown always wins - DuckDB is a derived view.
- If markdown and DuckDB disagree, re-extract from markdown
- DuckDB can be fully regenerated from notes at any time
- No manual database edits expected; if needed, edit the source markdown

### Schema Evolution
**Decision:** Additive only - new columns default to NULL.
- Adding new columns does not require migrations
- Existing records get NULL for new columns
- Re-extraction can populate new columns for historical data if desired
- No breaking changes to existing data

### Privacy Filtering
**Decision:** No filtering - all markdown files are sent to Claude for extraction.
- Simplifies implementation
- Users should not store sensitive data in the vault if concerned
- Future: Could add opt-in filtering if needed

### ID Generation
**Decision:** Composite key pattern for exercise_log IDs.
- Format: `{activity_id}_{exercise_name}_{set_number}`
- Example: `20260131_str_1_squat_1`
- Deterministic: same content always produces same IDs
- Enables idempotent extraction (re-extracting replaces same rows)
- Exercise names normalized to snake_case (e.g., `leg_press` not `leg press`)

---

*Next: [05-LLM-INTEGRATION.md](./05-LLM-INTEGRATION.md)*
