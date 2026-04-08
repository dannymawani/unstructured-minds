"""Kanban API endpoints backed by DuckDB kanban_tasks table."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..db import DatabaseManager
from ..db.sql_compat import get_dialect, placeholder, user_filter
from .dependencies import get_db as _dep_get_db
from .dependencies import get_user_id

router = APIRouter(prefix="/kanban", tags=["kanban"])


# =============================================================================
# Models
# =============================================================================


class KanbanTask(BaseModel):
    id: str
    title: str
    phase: str | None = None
    priority: str | None = None
    status: str
    branch: str | None = None
    depends_on: str | None = None
    description: str | None = None
    content: str | None = None
    deadline: date | None = None
    completed_at: str | None = None


class KanbanColumn(BaseModel):
    name: str
    status: str
    tasks: list[KanbanTask]


class KanbanBoard(BaseModel):
    columns: list[KanbanColumn]


class KanbanTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    phase: str | None = None
    priority: str | None = None
    branch: str | None = None
    depends_on: str | None = None
    description: str | None = None
    content: str | None = None
    deadline: date | None = Field(None, description="Deadline date (YYYY-MM-DD)")


class KanbanTaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    phase: str | None = None
    priority: str | None = None
    status: str | None = Field(None, pattern=r"^(not_started|in_progress|done)$")
    branch: str | None = None
    depends_on: str | None = None
    description: str | None = None
    content: str | None = None
    deadline: date | None = Field(None, description="Deadline date (YYYY-MM-DD)")


class TaskNote(BaseModel):
    id: int
    task_id: str
    note: str
    created_at: str


class TaskNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


# =============================================================================
# Helpers
# =============================================================================

COLUMNS = [
    {"name": "Not Started", "status": "not_started"},
    {"name": "In Progress", "status": "in_progress"},
    {"name": "Done", "status": "done"},
]


def get_db(request: Request):
    return _dep_get_db(request)


def _row_to_task(row: tuple, columns: list[str]) -> KanbanTask:
    data = dict(zip(columns, row))
    return KanbanTask(
        id=data["id"],
        title=data["title"],
        phase=data.get("phase"),
        priority=data.get("priority"),
        status=data["status"],
        branch=data.get("branch"),
        depends_on=data.get("depends_on"),
        description=data.get("description"),
        content=data.get("content"),
        deadline=data["deadline"] if data.get("deadline") else None,
        completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/board", response_model=KanbanBoard)
async def get_kanban_board(
    phase: str | None = Query(None, description="Filter by phase"),
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> KanbanBoard:
    """Get the full kanban board. Single SQL query instead of filesystem scan."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions: list[str] = []
    params: list = []

    user_filter(dialect, user_id, conditions, params)

    if phase:
        conditions.append(f"phase LIKE {ph}")
        params.append(f"%{phase}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    result = db.execute(
        f"SELECT * FROM kanban_tasks {where} ORDER BY id",
        params,
    )
    col_names = [desc[0] for desc in result.description]
    rows = result.fetchall()

    # Group by status
    tasks_by_status: dict[str, list[KanbanTask]] = {c["status"]: [] for c in COLUMNS}
    for row in rows:
        task = _row_to_task(row, col_names)
        if task.status in tasks_by_status:
            tasks_by_status[task.status].append(task)

    columns = [
        KanbanColumn(name=c["name"], status=c["status"], tasks=tasks_by_status.get(c["status"], []))
        for c in COLUMNS
    ]
    return KanbanBoard(columns=columns)


@router.get("/task/{task_id}", response_model=KanbanTask)
async def get_task(
    task_id: str,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> KanbanTask:
    """Get a specific task by ID."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions = [f"id = {ph}"]
    params: list = [task_id]
    user_filter(dialect, user_id, conditions, params)
    result = db.execute(f"SELECT * FROM kanban_tasks WHERE {' AND '.join(conditions)}", params)
    col_names = [desc[0] for desc in result.description]
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return _row_to_task(row, col_names)


@router.post("/task/{task_id}/move")
async def move_task(
    task_id: str,
    new_status: str = Query(..., description="Target status"),
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> dict:
    """Move a task to a different status column."""
    if new_status not in ("not_started", "in_progress", "done"):
        raise HTTPException(status_code=400, detail="Invalid status")

    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions = [f"id = {ph}"]
    params: list = [task_id]
    user_filter(dialect, user_id, conditions, params)

    result = db.execute(f"SELECT id FROM kanban_tasks WHERE {' AND '.join(conditions)}", params)
    if not result.fetchone():
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    completed_at = datetime.now().isoformat() if new_status == "done" else None
    update_conds = [f"id = {ph}"]
    update_params: list = [new_status, completed_at, task_id]
    user_filter(dialect, user_id, update_conds, update_params)
    db.execute(
        f"UPDATE kanban_tasks SET status = {ph}, completed_at = {ph} WHERE {' AND '.join(update_conds)}",
        update_params,
    )

    return {"success": True, "task_id": task_id, "new_status": new_status}


@router.post("/task", response_model=KanbanTask, status_code=201)
async def create_task(
    request: KanbanTaskCreate,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> KanbanTask:
    """Create a new kanban task."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    # Generate ID from title
    task_id = request.title.lower().replace(" ", "-").replace("/", "-")[:60]

    # Check for duplicate
    dup_conds = [f"id = {ph}"]
    dup_params: list = [task_id]
    user_filter(dialect, user_id, dup_conds, dup_params)
    result = db.execute(f"SELECT id FROM kanban_tasks WHERE {' AND '.join(dup_conds)}", dup_params)
    if result.fetchone():
        raise HTTPException(status_code=409, detail=f"Task with id '{task_id}' already exists")

    cols = ["id", "title", "phase", "priority", "status", "branch", "depends_on", "description", "content", "deadline"]
    vals: list = [task_id, request.title, request.phase, request.priority, "not_started",
                  request.branch, request.depends_on, request.description, request.content, request.deadline]
    if dialect == "postgres":
        cols.append("user_id")
        vals.append(user_id)
    placeholders = ", ".join([ph] * len(cols))
    db.execute(f"INSERT INTO kanban_tasks ({', '.join(cols)}) VALUES ({placeholders})", vals)

    fetch_conds = [f"id = {ph}"]
    fetch_params: list = [task_id]
    user_filter(dialect, user_id, fetch_conds, fetch_params)
    result = db.execute(f"SELECT * FROM kanban_tasks WHERE {' AND '.join(fetch_conds)}", fetch_params)
    col_names = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_task(row, col_names)


@router.patch("/task/{task_id}", response_model=KanbanTask)
async def update_task(
    task_id: str,
    request: KanbanTaskUpdate,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> KanbanTask:
    """Update a kanban task's fields."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    check_conds = [f"id = {ph}"]
    check_params: list = [task_id]
    user_filter(dialect, user_id, check_conds, check_params)
    result = db.execute(f"SELECT id FROM kanban_tasks WHERE {' AND '.join(check_conds)}", check_params)
    if not result.fetchone():
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    updates = []
    values: list = []
    for field in ("title", "phase", "priority", "status", "branch", "depends_on", "description", "content", "deadline"):
        val = getattr(request, field, None)
        if val is not None:
            updates.append(f"{field} = {ph}")
            values.append(val)

    if request.status == "done":
        updates.append(f"completed_at = {ph}")
        values.append(datetime.now().isoformat())

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    where_conds = [f"id = {ph}"]
    values.append(task_id)
    user_filter(dialect, user_id, where_conds, values)
    db.execute(f"UPDATE kanban_tasks SET {', '.join(updates)} WHERE {' AND '.join(where_conds)}", values)

    fetch_conds = [f"id = {ph}"]
    fetch_params: list = [task_id]
    user_filter(dialect, user_id, fetch_conds, fetch_params)
    result = db.execute(f"SELECT * FROM kanban_tasks WHERE {' AND '.join(fetch_conds)}", fetch_params)
    col_names = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_task(row, col_names)


@router.delete("/task/{task_id}")
async def delete_task(
    task_id: str,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> dict:
    """Delete a kanban task."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    check_conds = [f"id = {ph}"]
    check_params: list = [task_id]
    user_filter(dialect, user_id, check_conds, check_params)
    result = db.execute(f"SELECT id FROM kanban_tasks WHERE {' AND '.join(check_conds)}", check_params)
    if not result.fetchone():
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    del_conds = [f"id = {ph}"]
    del_params: list = [task_id]
    user_filter(dialect, user_id, del_conds, del_params)
    db.execute(f"DELETE FROM kanban_tasks WHERE {' AND '.join(del_conds)}", del_params)

    upd_conds = [f"task_id = {ph}"]
    upd_params: list = [task_id]
    user_filter(dialect, user_id, upd_conds, upd_params)
    db.execute(f"DELETE FROM kanban_task_updates WHERE {' AND '.join(upd_conds)}", upd_params)
    return {"success": True, "task_id": task_id}


@router.get("/task/{task_id}/updates", response_model=list[TaskNote])
async def list_task_updates(
    task_id: str,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> list[TaskNote]:
    """List all status updates / notes for a task, newest first."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    conditions = [f"task_id = {ph}"]
    params: list = [task_id]
    user_filter(dialect, user_id, conditions, params)
    result = db.execute(
        f"SELECT id, task_id, note, created_at FROM kanban_task_updates WHERE {' AND '.join(conditions)} ORDER BY created_at DESC",
        params,
    )
    return [
        TaskNote(id=row[0], task_id=row[1], note=row[2], created_at=str(row[3]))
        for row in result.fetchall()
    ]


@router.post("/task/{task_id}/updates", response_model=TaskNote, status_code=201)
async def add_task_update(
    task_id: str,
    request: TaskNoteCreate,
    db: DatabaseManager = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> TaskNote:
    """Add a status update / note to a task."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    # Verify task exists
    check_conds = [f"id = {ph}"]
    check_params: list = [task_id]
    user_filter(dialect, user_id, check_conds, check_params)
    check = db.execute(f"SELECT id FROM kanban_tasks WHERE {' AND '.join(check_conds)}", check_params)
    if not check.fetchone():
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if dialect == "postgres":
        vals = [task_id, request.note, user_id]
        result = db.execute(
            "INSERT INTO kanban_task_updates (task_id, note, user_id) VALUES (%s, %s, %s) RETURNING id, task_id, note, created_at",
            vals,
        )
        row = result.fetchone()
    else:
        max_id = db.execute("SELECT COALESCE(MAX(id), 0) FROM kanban_task_updates").fetchone()[0]
        new_id = max_id + 1
        db.execute(
            "INSERT INTO kanban_task_updates (id, task_id, note) VALUES (?, ?, ?)",
            [new_id, task_id, request.note],
        )
        result = db.execute(
            "SELECT id, task_id, note, created_at FROM kanban_task_updates WHERE id = ?",
            [new_id],
        )
        row = result.fetchone()

    return TaskNote(id=row[0], task_id=row[1], note=row[2], created_at=str(row[3]))
