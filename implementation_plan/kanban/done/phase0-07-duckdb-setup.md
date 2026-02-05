# DuckDB Setup

**Phase:** 0 - Foundation
**Priority:** Critical
**Completed:** 2026-01-31

## Description

Set up DuckDB as the analytics database with schema definitions for all extracted data types.

## Tasks

- [x] Create schema.py with table definitions
- [x] Add connection manager with pooling
- [x] Create migration/versioning system
- [x] Define tables: exercise_log, daily_metrics, extraction_log, etc.

## Acceptance Criteria

- Tables created on database init
- Can connect and query
- Schema versions tracked
- All data types from extraction have corresponding tables

## Key Files

- `backend/src/db/schema.py`
- `backend/src/db/connection.py`

## Schema Tables

- `exercise_log` - Workout data
- `daily_metrics` - Sleep, weight, mood
- `extraction_log` - Track what's been processed
- `food_log` - Nutrition data
- `daily_tasks` - Task tracking
