"""Personal task API endpoints backed by DuckDB tasks table."""

import re
import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..db import DatabaseManager
from ..db.sql_compat import get_dialect, placeholder, user_filter
from ..storage import StorageBackend
from .dependencies import get_db as _dep_get_db
from .dependencies import get_storage as _dep_get_storage
from .dependencies import get_user_id
from .settings import resolve_daily_note_path

router = APIRouter(prefix="/tasks", tags=["tasks"])


# =============================================================================
# Models
# =============================================================================


class TaskOut(BaseModel):
    id: str
    date: str
    description: str
    status: str | None = None
    completed_at: str | None = None
    category: str | None = None
    priority: int | None = None
    source_file: str | None = None
    deadline: str | None = None
    notes: str | None = None


class TaskListResponse(BaseModel):
    tasks: list[TaskOut]
    total: int


class TaskUpdateRequest(BaseModel):
    status: str | None = Field(None, pattern=r"^(backlog|in_progress|done|cancelled)$")
    description: str | None = Field(None, min_length=1, max_length=500)
    category: str | None = None
    priority: int | None = Field(None, ge=1, le=3)
    deadline: date | None = None
    notes: str | None = Field(None, max_length=5000)


class TaskCreateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    category: str | None = None
    priority: int | None = Field(None, ge=1, le=3)
    deadline: date | None = None
    notes: str | None = Field(None, max_length=5000)


class BulkCompleteRequest(BaseModel):
    statuses: list[str] = Field(
        default=["backlog", "in_progress"],
        description="Which statuses to mark as done",
    )
    backdate_days: int = Field(
        default=8,
        ge=0,
        le=365,
        description="Backdate completed_at by this many days so tasks are hidden by hide_old filter",
    )


class BulkCompleteResponse(BaseModel):
    updated: int


class RolloverTaskOut(BaseModel):
    id: str
    date: str
    description: str
    status: str
    category: str | None = None
    priority: int | None = None
    deadline: str | None = None
    deadline_status: str | None = None  # "overdue" | "due_today" | "upcoming" | None
    auto_select: bool = False  # True for in_progress + overdue/due_today


class RolloverResponse(BaseModel):
    tasks: list[RolloverTaskOut]
    total: int


class RolloverCommitRequest(BaseModel):
    task_ids: list[str]
    new_source_file: str


class RolloverCommitResponse(BaseModel):
    updated: int


# =============================================================================
# Helpers
# =============================================================================


def get_db(request: Request):
    return _dep_get_db(request)


def get_storage(request: Request) -> StorageBackend:
    return _dep_get_storage(request)


def _row_to_task(row: tuple, columns: list[str]) -> TaskOut:
    data = dict(zip(columns, row))
    return TaskOut(
        id=data["id"],
        date=str(data["date"]),
        description=data["description"],
        status=data.get("status"),
        completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
        category=data.get("category"),
        priority=data.get("priority"),
        source_file=data.get("source_file"),
        deadline=str(data["deadline"]) if data.get("deadline") else None,
        notes=data.get("notes"),
    )


async def _sync_task_to_markdown(
    storage: StorageBackend,
    source_file: str,
    description: str,
    new_status: str,
) -> None:
    """Update the checkbox in the source markdown file to match the new status."""
    try:
        content_bytes = await storage.read(source_file)
        content = content_bytes.decode("utf-8")
    except (FileNotFoundError, ValueError):
        return

    checked = new_status == "done"
    old_pattern = r"- \[([ xX])\] " + re.escape(description)
    new_checkbox = f"- [{'x' if checked else ' '}] {description}"
    updated = re.sub(old_pattern, new_checkbox, content, count=1)

    if updated != content:
        await storage.write(source_file, updated.encode("utf-8"))


async def _sync_description_to_markdown(
    storage: StorageBackend,
    source_file: str,
    old_description: str,
    new_description: str,
    current_status: str,
) -> None:
    """Rename a task's text in the source markdown file."""
    try:
        content_bytes = await storage.read(source_file)
        content = content_bytes.decode("utf-8")
    except (FileNotFoundError, ValueError):
        return

    checked = current_status == "done"
    checkbox = "x" if checked else " "
    old_line = f"- [{checkbox}] {old_description}"
    new_line = f"- [{checkbox}] {new_description}"
    # Also try matching the opposite checkbox state in case of mismatch
    updated = content.replace(old_line, new_line, 1)
    if updated == content:
        alt_checkbox = " " if checked else "x"
        old_line_alt = f"- [{alt_checkbox}] {old_description}"
        new_line_alt = f"- [{alt_checkbox}] {new_description}"
        updated = content.replace(old_line_alt, new_line_alt, 1)

    if updated != content:
        await storage.write(source_file, updated.encode("utf-8"))


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = Query(None, description="Filter by status"),
    category: str | None = Query(None, description="Filter by category"),
    date_from: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    hide_old: bool = Query(True, description="Hide done/cancelled tasks older than 7 days"),
    done_limit: int = Query(10, ge=0, le=100, description="Max done/cancelled tasks to return"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> TaskListResponse:
    """List personal tasks with optional filters.

    Done/cancelled tasks are capped at `done_limit` (default 10) most recent,
    and hidden entirely after 7 days when `hide_old` is true.
    """
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    # When fetching all statuses (no filter), query active and done separately
    # so we can cap done tasks at done_limit.
    if not status:
        # Active tasks (backlog, in_progress) — no cap
        active_conds: list[str] = ["status IN ('backlog', 'in_progress')"]
        active_params: list = []
        user_filter(dialect, user_id, active_conds, active_params)
        if category:
            active_conds.append(f"category = {ph}")
            active_params.append(category)
        if date_from:
            active_conds.append(f"date >= {ph}")
            active_params.append(date_from)
        if date_to:
            active_conds.append(f"date <= {ph}")
            active_params.append(date_to)
        active_where = " AND ".join(active_conds)

        active_result = db.execute(
            f"SELECT * FROM tasks WHERE {active_where} ORDER BY date DESC, id",
            active_params,
        )
        active_cols = [desc[0] for desc in active_result.description]
        active_rows = active_result.fetchall()

        # Done/cancelled tasks — capped and filtered by age
        done_conds: list[str] = ["status IN ('done', 'cancelled')"]
        done_params: list = []
        user_filter(dialect, user_id, done_conds, done_params)
        if hide_old:
            done_conds.append(f"(completed_at IS NULL OR completed_at >= {ph})")
            done_params.append((datetime.now() - timedelta(days=7)).isoformat())
        if category:
            done_conds.append(f"category = {ph}")
            done_params.append(category)
        if date_from:
            done_conds.append(f"date >= {ph}")
            done_params.append(date_from)
        if date_to:
            done_conds.append(f"date <= {ph}")
            done_params.append(date_to)
        done_where = " AND ".join(done_conds)

        done_result = db.execute(
            f"SELECT * FROM tasks WHERE {done_where} ORDER BY completed_at DESC NULLS LAST, date DESC LIMIT {ph}",
            done_params + [done_limit],
        )
        done_cols = [desc[0] for desc in done_result.description]
        done_rows = done_result.fetchall()

        all_tasks = (
            [_row_to_task(row, active_cols) for row in active_rows]
            + [_row_to_task(row, done_cols) for row in done_rows]
        )
        total = len(all_tasks)
        # Apply pagination to the combined result
        paginated = all_tasks[offset:offset + limit]
        return TaskListResponse(tasks=paginated, total=total)

    # Single-status filter — simple query
    conditions: list[str] = []
    params: list = []
    user_filter(dialect, user_id, conditions, params)

    if hide_old and status in ("done", "cancelled"):
        conditions.append(f"(completed_at IS NULL OR completed_at >= {ph})")
        params.append((datetime.now() - timedelta(days=7)).isoformat())

    conditions.append(f"status = {ph}")
    params.append(status)
    if category:
        conditions.append(f"category = {ph}")
        params.append(category)
    if date_from:
        conditions.append(f"date >= {ph}")
        params.append(date_from)
    if date_to:
        conditions.append(f"date <= {ph}")
        params.append(date_to)

    where = " AND ".join(conditions)
    where_clause = f"WHERE {where}" if where else ""

    count_result = db.execute(f"SELECT COUNT(*) FROM tasks {where_clause}", params)
    total = count_result.fetchone()[0]

    result = db.execute(
        f"SELECT * FROM tasks {where_clause} ORDER BY completed_at DESC NULLS LAST, date DESC, id LIMIT {ph} OFFSET {ph}",
        params + [limit, offset],
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    tasks = [_row_to_task(row, columns) for row in rows]
    return TaskListResponse(tasks=tasks, total=total)


@router.get("/rollover", response_model=RolloverResponse)
async def get_rollover_tasks(
    target_date: str = Query(..., description="Target date for the new daily note (YYYY-MM-DD)"),
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> RolloverResponse:
    """Get incomplete tasks from the last 14 days eligible for rollover."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    try:
        target = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    window_start = (target - timedelta(days=14)).isoformat()

    conditions: list[str] = [
        "status IN ('backlog', 'in_progress')",
        f"date >= {ph}",
        f"date < {ph}",
    ]
    params: list = [window_start, target_date]
    user_filter(dialect, user_id, conditions, params)
    where = " AND ".join(conditions)

    result = db.execute(
        f"SELECT * FROM tasks WHERE {where} ORDER BY date DESC, id",
        params,
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    today = target
    rollover_tasks: list[RolloverTaskOut] = []
    for row in rows:
        data = dict(zip(columns, row))
        deadline_status = None
        auto_select = False

        if data.get("deadline"):
            try:
                dl = date.fromisoformat(str(data["deadline"]))
                if dl < today:
                    deadline_status = "overdue"
                elif dl == today:
                    deadline_status = "due_today"
                else:
                    deadline_status = "upcoming"
            except ValueError:
                pass

        if data.get("status") == "in_progress":
            auto_select = True
        if deadline_status in ("overdue", "due_today"):
            auto_select = True

        rollover_tasks.append(RolloverTaskOut(
            id=data["id"],
            date=str(data["date"]),
            description=data["description"],
            status=data.get("status", "backlog"),
            category=data.get("category"),
            priority=data.get("priority"),
            deadline=str(data["deadline"]) if data.get("deadline") else None,
            deadline_status=deadline_status,
            auto_select=auto_select,
        ))

    # Sort: overdue first, then due_today, then in_progress, then backlog by date desc
    status_order = {"overdue": 0, "due_today": 1, "upcoming": 3, None: 3}

    def sort_key(t: RolloverTaskOut):
        dl_order = status_order.get(t.deadline_status, 3)
        status_boost = 0 if t.status == "in_progress" else 1
        return (dl_order, status_boost, t.date)

    rollover_tasks.sort(key=sort_key)

    return RolloverResponse(tasks=rollover_tasks, total=len(rollover_tasks))


@router.post("/rollover", response_model=RolloverCommitResponse)
async def commit_rollover_tasks(
    request: RolloverCommitRequest,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> RolloverCommitResponse:
    """Update source_file for rolled-over tasks to point to the new daily note."""
    if not request.task_ids:
        return RolloverCommitResponse(updated=0)

    dialect = get_dialect(db)
    ph = placeholder(dialect)

    id_placeholders = ", ".join(ph for _ in request.task_ids)
    conditions = [f"id IN ({id_placeholders})"]
    params: list = list(request.task_ids)
    user_filter(dialect, user_id, conditions, params)
    where = " AND ".join(conditions)

    count_result = db.execute(f"SELECT COUNT(*) FROM tasks WHERE {where}", params)
    count = count_result.fetchone()[0]

    if count > 0:
        update_params: list = [request.new_source_file] + list(request.task_ids)
        update_conds = [f"id IN ({id_placeholders})"]
        user_filter(dialect, user_id, update_conds, update_params)
        db.execute(
            f"UPDATE tasks SET source_file = {ph} WHERE {' AND '.join(update_conds)}",
            update_params,
        )

    return RolloverCommitResponse(updated=count)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> TaskOut:
    """Get a single task by ID."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions = [f"id = {ph}"]
    params: list = [task_id]
    user_filter(dialect, user_id, conditions, params)
    result = db.execute(f"SELECT * FROM tasks WHERE {' AND '.join(conditions)}", params)
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return _row_to_task(row, columns)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    user_id: str = Depends(get_user_id),
) -> TaskOut:
    """Update a task's status, category, or priority. Syncs checkbox in source markdown."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    # Fetch existing task
    fetch_conds = [f"id = {ph}"]
    fetch_params: list = [task_id]
    user_filter(dialect, user_id, fetch_conds, fetch_params)
    result = db.execute(f"SELECT * FROM tasks WHERE {' AND '.join(fetch_conds)}", fetch_params)
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    existing = dict(zip(columns, row))

    # Build update
    updates = []
    values: list = []
    if request.status is not None:
        updates.append(f"status = {ph}")
        values.append(request.status)
        if request.status in ("done", "cancelled"):
            updates.append(f"completed_at = {ph}")
            values.append(datetime.now().isoformat())
        elif existing.get("completed_at"):
            updates.append("completed_at = NULL")
    if request.description is not None:
        updates.append(f"description = {ph}")
        values.append(request.description)
    if request.category is not None:
        updates.append(f"category = {ph}")
        values.append(request.category)
    if request.priority is not None:
        updates.append(f"priority = {ph}")
        values.append(request.priority)
    if request.deadline is not None:
        updates.append(f"deadline = {ph}")
        values.append(request.deadline)
    if request.notes is not None:
        updates.append(f"notes = {ph}")
        values.append(request.notes)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    where_conds = [f"id = {ph}"]
    values.append(task_id)
    user_filter(dialect, user_id, where_conds, values)
    db.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE {' AND '.join(where_conds)}", values)

    # Two-way sync: update checkbox in source markdown
    if existing.get("source_file"):
        if request.description is not None and request.description != existing["description"]:
            await _sync_description_to_markdown(
                storage,
                existing["source_file"],
                existing["description"],
                request.description,
                existing.get("status") or "backlog",
            )
        if request.status is not None:
            desc = request.description if request.description is not None else existing["description"]
            await _sync_task_to_markdown(
                storage,
                existing["source_file"],
                desc,
                request.status,
            )

    # Return updated task
    refetch_conds = [f"id = {ph}"]
    refetch_params: list = [task_id]
    user_filter(dialect, user_id, refetch_conds, refetch_params)
    result = db.execute(f"SELECT * FROM tasks WHERE {' AND '.join(refetch_conds)}", refetch_params)
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_task(row, columns)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    user_id: str = Depends(get_user_id),
) -> None:
    """Delete a task by ID and remove from source markdown."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions = [f"id = {ph}"]
    params: list = [task_id]
    user_filter(dialect, user_id, conditions, params)
    result = db.execute(f"SELECT * FROM tasks WHERE {' AND '.join(conditions)}", params)
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    task = dict(zip(columns, row))
    db.execute(f"DELETE FROM tasks WHERE {' AND '.join(conditions)}", params)

    # Remove checkbox from source markdown
    if task.get("source_file"):
        try:
            content_bytes = await storage.read(task["source_file"])
            content = content_bytes.decode("utf-8")

            description = task["description"]
            status = task.get("status", "backlog")
            checkbox = "x" if status == "done" else " "
            pattern = rf"^- \[{re.escape(checkbox)}\] {re.escape(description)}\n?"
            updated = re.sub(pattern, "", content, count=1, flags=re.MULTILINE)

            # Try opposite checkbox state as fallback
            if updated == content:
                alt_checkbox = " " if status == "done" else "x"
                pattern = rf"^- \[{re.escape(alt_checkbox)}\] {re.escape(description)}\n?"
                updated = re.sub(pattern, "", content, count=1, flags=re.MULTILINE)

            if updated != content:
                await storage.write(task["source_file"], updated.encode("utf-8"))
        except (FileNotFoundError, ValueError):
            pass  # Task deleted from DB even if markdown sync fails


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    request: TaskCreateRequest,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    user_id: str = Depends(get_user_id),
) -> TaskOut:
    """Create a new task. Adds to DB and appends to today's daily note."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    task_id = f"{now.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

    daily_note_path = resolve_daily_note_path(date_str)

    cols = ["id", "date", "description", "status", "category", "priority", "source_file", "deadline", "notes"]
    vals: list = [task_id, date_str, request.description, "backlog", request.category,
                  request.priority, daily_note_path, request.deadline, request.notes]
    if dialect == "postgres":
        cols.append("user_id")
        vals.append(user_id)
    placeholders = ", ".join([ph] * len(cols))
    db.execute(f"INSERT INTO tasks ({', '.join(cols)}) VALUES ({placeholders})", vals)

    # Append to today's daily note
    try:
        task_line = f"- [ ] {request.description}\n"

        if await storage.exists(daily_note_path):
            content_bytes = await storage.read(daily_note_path)
            content = content_bytes.decode("utf-8")

            # Find tasks section or append at end
            tasks_pattern = r"(## (?:Tasks|To.?Do|Action Items)\n)"
            match = re.search(tasks_pattern, content, re.IGNORECASE)
            if match:
                insert_pos = match.end()
                content = content[:insert_pos] + task_line + content[insert_pos:]
            else:
                content = content.rstrip() + "\n\n## Tasks\n" + task_line
            await storage.write(daily_note_path, content.encode("utf-8"))
    except Exception:
        pass  # Task is in DB even if markdown append fails

    fetch_conds = [f"id = {ph}"]
    fetch_params: list = [task_id]
    user_filter(dialect, user_id, fetch_conds, fetch_params)
    result = db.execute(f"SELECT * FROM tasks WHERE {' AND '.join(fetch_conds)}", fetch_params)
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_task(row, columns)


@router.post("/bulk-complete", response_model=BulkCompleteResponse)
async def bulk_complete_tasks(
    request: BulkCompleteRequest,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> BulkCompleteResponse:
    """Mark all tasks matching given statuses as done with backdated completed_at.

    Backdating ensures tasks are hidden by the default hide_old filter (7 days).
    """
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    valid_statuses = {"backlog", "in_progress", "done", "cancelled"}
    for s in request.statuses:
        if s not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {s}")

    if not request.statuses:
        return BulkCompleteResponse(updated=0)

    status_placeholders = ", ".join(ph for _ in request.statuses)
    completed_at = (datetime.now() - timedelta(days=request.backdate_days)).isoformat()

    conditions = [f"status IN ({status_placeholders})"]
    params: list = list(request.statuses)
    user_filter(dialect, user_id, conditions, params)
    where = " AND ".join(conditions)

    count_result = db.execute(f"SELECT COUNT(*) FROM tasks WHERE {where}", params)
    count = count_result.fetchone()[0]

    if count > 0:
        update_params: list = [completed_at] + list(request.statuses)
        update_conds = [f"status IN ({status_placeholders})"]
        user_filter(dialect, user_id, update_conds, update_params)
        db.execute(
            f"UPDATE tasks SET status = 'done', completed_at = {ph} WHERE {' AND '.join(update_conds)}",
            update_params,
        )

    return BulkCompleteResponse(updated=count)


@router.delete("/clear-all")
async def clear_all_tasks(
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Delete all tasks for the current user.

    Clears tasks from both local DuckDB and PostgreSQL (cloud mode).
    """
    dialect = get_dialect(db)

    conditions: list[str] = []
    params: list = []
    user_filter(dialect, user_id, conditions, params)

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

    count_result = db.execute(f"SELECT COUNT(*) FROM tasks{where}", params)
    count = count_result.fetchone()[0]

    if count > 0:
        delete_params: list = []
        delete_conditions: list[str] = []
        user_filter(dialect, user_id, delete_conditions, delete_params)
        delete_where = f" WHERE {' AND '.join(delete_conditions)}" if delete_conditions else ""
        db.execute(f"DELETE FROM tasks{delete_where}", delete_params)

    return {"deleted": count}
