# Task API Endpoints

**Phase:** 7 - Task Integration
**Priority:** High
**Status:** Done
**Completed:** 2026-02-06
**Branch:** feature/task-integration

## Description

Create API endpoints for personal tasks extracted from daily notes: GET /tasks (query with filters), PATCH /tasks/{id} (update status with two-way markdown sync), POST /tasks (create new task in today's note).

## Tasks

- [x] Create GET /tasks endpoint with status, category, date_from, date_to, limit, offset params
- [x] Create GET /tasks/{id} endpoint
- [x] Create PATCH /tasks/{id} endpoint for status/category/priority updates
- [x] Implement two-way sync: status change updates source markdown checkbox
- [x] Create POST /tasks endpoint (adds to DuckDB + appends to today's daily note)
- [x] Write tests for all endpoints (test_tasks_api.py)
- [x] Register router in main.py

## Acceptance Criteria

- GET /tasks returns tasks with filtering
- PATCH /tasks/{id} updates DuckDB and source markdown
- POST /tasks creates entry in both note and DuckDB
- Two-way sync correctly updates checkboxes ([ ] <-> [x])
- All endpoints have test coverage

## Key Files

- `backend/src/api/routes.py`
- `backend/src/services/`
