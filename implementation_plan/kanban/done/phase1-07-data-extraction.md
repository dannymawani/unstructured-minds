# Data Extraction

**Phase:** 1 - Core MVP
**Priority:** Critical
**Completed:** 2026-02-02

## Description

Implement the extraction pipeline that converts markdown notes into structured data in DuckDB.

## Tasks

- [x] POST /extract endpoint
- [x] File watcher for auto-extraction on save
- [x] Claude-powered extraction with schemas
- [x] Upsert logic for DuckDB
- [x] extraction_log tracking to skip unchanged files
- [x] Content hash comparison

## Acceptance Criteria

- Manual extraction via API works
- File watcher triggers extraction on save
- Data correctly populates DuckDB tables
- Unchanged files skipped (hash check)

## Key Files

- `backend/src/extraction/pipeline.py`
- `backend/src/extraction/schemas.py`
- `backend/src/watcher/file_watcher.py`
- `backend/src/api/extraction.py`

## Extraction Types

- Exercise logs
- Daily metrics (sleep, weight, mood)
- Food logs
- Task completion
