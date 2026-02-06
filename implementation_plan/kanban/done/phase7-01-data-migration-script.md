# Data Migration Script

**Phase:** 7 - Data Integration
**Priority:** Critical
**Status:** Done
**Completed:** 2026-02-06
**Branch:** feature/data-integration

## Description

Create `scripts/migrate_existing_data.py` to scan `existing_data/data/` date-partitioned CSVs, transform columns (exercise->exercise_name, sets->set_number, duration_min->duration_minutes), deduplicate, and write flat CSVs to `data/`. Copy config files and update schemas.

## Tasks

- [x] Scan existing_data/data/{type}/{year}/{month}/{day}/ for all CSV files
- [x] Implement column mapping for exercise_log (exercise->exercise_name, sets->set_number)
- [x] Concatenate all partitioned CSVs into single flat files per type
- [x] Deduplicate by primary key (date + activity_id + exercise_name + set_number)
- [x] Sort by date ascending
- [x] Write output to data/ directory
- [x] Copy config files (exercise_definitions.json, training_config.json, injury_config.json)
- [x] Update exercise_log schema with new column names
- [x] Add validation report (row counts, errors)
- [x] Write tests for migration script

## Acceptance Criteria

- `scripts/migrate_existing_data.py` exists and runs without errors
- Flat CSVs in `data/` contain all rows from partitioned sources
- Column names match the new schema (exercise_name, set_number, duration_minutes)
- No duplicate rows
- Config files copied to `data/`
- Test coverage for migration logic

## Key Files

- `scripts/migrate_existing_data.py`
- `existing_data/data/schemas/exercise_log.json`
- `data/exercise_log.csv`
