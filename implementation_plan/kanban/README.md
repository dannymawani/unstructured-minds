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

## Viewing the Board

The Kanban board can be viewed in the web UI:

1. Start the backend: `cd backend && python -m uvicorn src.main:app --reload`
2. Start the frontend: `cd frontend && npm run dev`
3. Click the **Kanban** tab in the header

## API Endpoints

- `GET /kanban/board` - Get all tasks organized by column
- `GET /kanban/task/{id}` - Get a specific task
- `POST /kanban/task/{id}/move?new_status=<status>` - Move task to new column

## Current Status

| Column | Count |
|--------|-------|
| Done | 16 |
| In Progress | 0 |
| Not Started | 23 |
| **Total** | **39** |

## Phases Overview

- **Phase 0**: Foundation (complete)
- **Phase 1**: Core MVP (complete)
- **Phase 2**: Polish (in progress)
- **Phase 3**: Deployment
- **Phase 4**: Advanced Features
- **Phase 5**: Extensibility
