---
name: task-integration
description: Documents two task systems (dev kanban and personal tasks) and their integration. Covers API endpoints, two-way sync between markdown checkboxes and kanban, and personal task UI.
user-invocable: false
---

# Task Integration

## Overview

Unstructured Minds has two distinct task systems:

1. **Dev Tasks (Kanban)** — Development work items tracked as `.md` files in `implementation_plan/kanban/`
2. **Personal Tasks** — Tasks extracted from daily notes into DuckDB, displayed in a personal kanban UI

Both should be accessible from the app but serve different purposes.

## 1. Dev Tasks (Existing Kanban)

### Current State
- Tasks are `.md` files in `kanban/{not_started,in_progress,done}/`
- API endpoints exist: `GET /kanban/board`, `POST /kanban/task/{id}/move`
- UI exists with basic column view

### No Changes Needed
Dev kanban is working. Keep as-is.

## 2. Personal Tasks (New)

### Data Source
Personal tasks are extracted from daily notes by Claude. The `daily_tasks` table in DuckDB contains:

```
date, task_id, description, status, source_file, source_line
```

**Status values:** `pending`, `completed`, `cancelled`, `moved`

### New API Endpoints

**GET /tasks**
- Query params: `status`, `date_from`, `date_to`, `limit`
- Returns personal tasks from DuckDB
- Default: all pending tasks, sorted by date desc

```python
@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
):
    query = "SELECT * FROM daily_tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)
    return db.execute(query, params).fetchall()
```

**PATCH /tasks/{task_id}**
- Update task status
- Also updates the source markdown file (two-way sync)

```python
@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdateRequest):
    # 1. Update DuckDB
    db.execute(
        "UPDATE daily_tasks SET status = ? WHERE task_id = ?",
        [update.status, task_id]
    )
    # 2. Update source markdown (two-way sync)
    task = db.execute(
        "SELECT source_file, source_line FROM daily_tasks WHERE task_id = ?",
        [task_id]
    ).fetchone()
    if task and task.source_file:
        await sync_task_to_markdown(task.source_file, task.source_line, update.status)
```

**POST /tasks**
- Create a new task (adds to today's daily note and DuckDB)

### Two-Way Sync

When a personal task status changes in the kanban UI:

1. **Kanban → Markdown:** Update the checkbox in the source daily note
   - `pending` → `- [ ] description`
   - `completed` → `- [x] description`
   - `cancelled` → `- [-] description` (or strikethrough)
   - `moved` → `- [>] description -> moved to {date}`

2. **Markdown → DuckDB:** When a note is saved + extracted, Claude reads the checkboxes and updates the task status in DuckDB

### Sync Implementation

```python
async def sync_task_to_markdown(file_path: str, line_number: int, new_status: str):
    """Update a checkbox in a markdown file based on task status change."""
    content = await vault_service.read_file(file_path)
    lines = content.split('\n')

    if line_number < len(lines):
        line = lines[line_number]
        # Replace checkbox marker
        if new_status == "completed":
            lines[line_number] = line.replace("- [ ]", "- [x]")
        elif new_status == "pending":
            lines[line_number] = line.replace("- [x]", "- [ ]")
        elif new_status == "cancelled":
            lines[line_number] = line.replace("- [ ]", "- [-]")

        await vault_service.write_file(file_path, '\n'.join(lines))
```

## 3. Personal Task Kanban UI

### Layout

```
┌──────────────────────────────────────────────────────┐
│ My Tasks                              [+ New Task]   │
├─────────────┬─────────────┬─────────────┬───────────┤
│   Pending   │ In Progress │  Completed  │ Cancelled │
├─────────────┼─────────────┼─────────────┼───────────┤
│ ┌─────────┐ │             │ ┌─────────┐ │           │
│ │ Call     │ │             │ │ Review  │ │           │
│ │ dentist  │ │             │ │ PR      │ │           │
│ │ Jan 15   │ │             │ │ Jan 15  │ │           │
│ └─────────┘ │             │ └─────────┘ │           │
│ ┌─────────┐ │             │             │           │
│ │ Buy      │ │             │             │           │
│ │ groceries│ │             │             │           │
│ │ Jan 16   │ │             │             │           │
│ └─────────┘ │             │             │           │
└─────────────┴─────────────┴─────────────┴───────────┘
```

### Features

- **Drag-and-drop** between columns to change status
- **Click** a task card to see full details and source note link
- **Source link** on each card: "From: 2026-01-15.md" — clicking opens the note
- **Date grouping** or **date filter** to focus on specific time ranges
- **New Task** button: creates a task entry in today's daily note
- **Search/filter** by description text

### Task Card Component

```tsx
interface TaskCard {
  task_id: string;
  description: string;
  date: string;
  status: "pending" | "completed" | "cancelled" | "moved";
  source_file?: string;
  source_line?: number;
}
```

### Drag-and-Drop

Use a lightweight drag-and-drop library compatible with React 19:
- `@dnd-kit/core` + `@dnd-kit/sortable` (recommended, tree-shakable)
- On drop: call `PATCH /tasks/{task_id}` with new status
- Optimistic UI update, revert on API error

## Implementation Priority

1. **Task API endpoints** — Foundation for everything else
2. **Personal task kanban UI** — Primary user-facing feature
3. **Two-way sync** — Can be added incrementally
