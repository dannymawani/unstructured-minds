# Kanban Task Board

This folder contains the implementation tasks organized as a kanban board.

## Structure

```
kanban/
├── not_started/    # Tasks ready to be worked on
├── in_progress/    # Tasks currently being worked on
└── done/           # Completed tasks
```

## Task File Format

Each task is a markdown file with the following structure:

```markdown
# Task Title

**Phase:** N - Phase Name
**Priority:** Critical | High | Medium | Low
**Status:** Not Started | In Progress | Done

## Description

Brief description of what needs to be done.

## Tasks

- [ ] Subtask 1
- [ ] Subtask 2

## Acceptance Criteria

- Criterion 1
- Criterion 2
```

## Storage

Tasks are stored in the DuckDB `kanban_tasks` table. The markdown files in this directory are the original source but the canonical data now lives in DuckDB.

To re-import from markdown files: `python3 scripts/migrate_kanban_to_duckdb.py`

## Viewing the Board

1. Start with Docker: `docker compose -f docker-compose.dev.yml up`
2. Open http://localhost:5173
3. Click the **Kanban** tab in the header

## API Endpoints

- `GET /kanban/board` - Get all tasks organized by column (with optional `?phase=` filter)
- `GET /kanban/task/{id}` - Get a specific task
- `POST /kanban/task/{id}/move?new_status=<status>` - Move task to new column
- `POST /kanban/task` - Create a new task
- `PATCH /kanban/task/{id}` - Update task fields
- `DELETE /kanban/task/{id}` - Delete a task

## Phases Overview

- **Phase 0**: Foundation (complete)
- **Phase 1**: Core MVP (complete)
- **Phase 2**: Polish (complete)
- **Phase 3**: Deployment
- **Phase 4**: Advanced Features
- **Phase 5**: Extensibility
- **Phase 6**: Before Starting (complete) - Docker validation, skills, design manual
- **Phase 7**: Data Integration & Features (complete) - Data migration, extraction timing, editor UX, task integration
