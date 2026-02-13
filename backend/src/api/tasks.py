"""Personal task API endpoints backed by DuckDB tasks table."""

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import DatabaseManager
from ..db.sql_compat import get_dialect, placeholder, user_filter
from ..storage import StorageBackend
from .dependencies import get_db as _dep_get_db, get_storage as _dep_get_storage, get_user_id
from .settings import resolve_daily_note_path

router = APIRouter(prefix="/tasks", tags=["tasks"])


# =============================================================================
# Models
# =============================================================================


class TaskOut(BaseModel):
    id: str
    date: str
    description: str
    status: Optional[str] = None
    completed_at: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    source_file: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None


class TaskListResponse(BaseModel):
    tasks: list[TaskOut]
    total: int


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, pattern=r"^(backlog|in_progress|done|cancelled)$")
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    deadline: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=5000)


class TaskCreateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    deadline: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=5000)


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
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    hide_old: bool = Query(True, description="Hide done/cancelled tasks older than 7 days"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> TaskListResponse:
    """List personal tasks with optional filters."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions: list[str] = []
    params: list = []

    user_filter(dialect, user_id, conditions, params)

    if hide_old and not status:
        conditions.append(
            f"(status NOT IN ('done', 'cancelled') OR completed_at IS NULL OR completed_at >= {ph})"
        )
        params.append((datetime.now() - timedelta(days=7)).isoformat())

    if status:
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
        f"SELECT * FROM tasks {where_clause} ORDER BY date DESC, id LIMIT {ph} OFFSET {ph}",
        params + [limit, offset],
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    tasks = [_row_to_task(row, columns) for row in rows]
    return TaskListResponse(tasks=tasks, total=total)


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
