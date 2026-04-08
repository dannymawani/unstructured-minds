---
name: clear-tasks
description: Bulk-complete stale personal tasks to clean up the kanban board. Use when the board is cluttered with old tasks.
allowed-tools: Bash(duckdb *), Bash(curl *)
---

# Clear Tasks

Bulk-complete stale personal tasks so they disappear from the kanban board.

## How It Works

The `hide_old` filter (default=true) hides done/cancelled tasks with `completed_at` older than 7 days. By marking tasks as "done" with a backdated `completed_at`, they automatically disappear from the board.

## Database

- **Path**: `data/unstructured.duckdb`
- **Table**: `tasks`
- **Key columns**: `status`, `completed_at`

## Execution

### Step 1: Show current task counts

```bash
duckdb data/unstructured.duckdb -c "SELECT status, COUNT(*) as count FROM tasks GROUP BY status ORDER BY count DESC;"
```

### Step 2: Confirm with user what to clear

Ask the user which statuses to clear. Default is `backlog` and `in_progress`.

### Step 3: Run the bulk update

Backdate `completed_at` by 8 days (1 day past the 7-day hide threshold):

```bash
duckdb data/unstructured.duckdb -c "UPDATE tasks SET status = 'done', completed_at = (NOW() - INTERVAL 8 DAY)::TIMESTAMP::VARCHAR WHERE status IN ('backlog', 'in_progress');"
```

Adjust the `WHERE` clause based on user preference (e.g., only `backlog`, include `cancelled`, etc.).

### Step 4: Verify

```bash
duckdb data/unstructured.duckdb -c "SELECT status, COUNT(*) as count FROM tasks GROUP BY status ORDER BY count DESC;"
```

### Alternative: API Endpoint

If the backend is running, use the bulk-complete API:

```bash
curl -X POST http://localhost:8000/tasks/bulk-complete \
  -H "Content-Type: application/json" \
  -d '{"statuses": ["backlog", "in_progress"], "backdate_days": 8}'
```

Response: `{"updated": N}` where N is the number of tasks marked as done.

## Arguments

$ARGUMENTS
