"""Kanban API endpoints backed by DuckDB kanban_tasks table."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..db import DatabaseManager

router = APIRouter(prefix="/kanban", tags=["kanban"])


# =============================================================================
# Models
# =============================================================================


class KanbanTask(BaseModel):
    id: str
    title: str
    phase: Optional[str] = None
    priority: Optional[str] = None
    status: str
    branch: Optional[str] = None
    depends_on: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    deadline: Optional[str] = None
    completed_at: Optional[str] = None


class KanbanColumn(BaseModel):
    name: str
    status: str
    tasks: list[KanbanTask]


class KanbanBoard(BaseModel):
    columns: list[KanbanColumn]


class KanbanTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    phase: Optional[str] = None
    priority: Optional[str] = None
    branch: Optional[str] = None
    depends_on: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    deadline: Optional[str] = Field(None, max_length=100, description="Deadline (e.g. 'Friday', '2026-02-14', 'end of sprint')")


class KanbanTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    phase: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(not_started|in_progress|done)$")
    branch: Optional[str] = None
    depends_on: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    deadline: Optional[str] = Field(None, max_length=100)


# =============================================================================
# Helpers
# =============================================================================

COLUMNS = [
    {"name": "Not Started", "status": "not_started"},
    {"name": "In Progress", "status": "in_progress"},
    {"name": "Done", "status": "done"},
]


def get_db(request: Request) -> DatabaseManager:
    return request.app.state.db


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
        deadline=data.get("deadline"),
        completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/board", response_model=KanbanBoard)
async def get_kanban_board(
    phase: Optional[str] = Query(None, description="Filter by phase"),
    db: DatabaseManager = Depends(get_db),
) -> KanbanBoard:
    """Get the full kanban board. Single SQL query instead of filesystem scan."""
    conditions = []
    params: list = []

    if phase:
        conditions.append("phase LIKE ?")
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
) -> KanbanTask:
    """Get a specific task by ID."""
    result = db.execute("SELECT * FROM kanban_tasks WHERE id = ?", [task_id])
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
) -> dict:
    """Move a task to a different status column."""
    if new_status not in ("not_started", "in_progress", "done"):
        raise HTTPException(status_code=400, detail="Invalid status")

    result = db.execute("SELECT id FROM kanban_tasks WHERE id = ?", [task_id])
    if not result.fetchone():
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    completed_at = datetime.now().isoformat() if new_status == "done" else None
    db.execute(
        "UPDATE kanban_tasks SET status = ?, completed_at = ? WHERE id = ?",
        [new_status, completed_at, task_id],
    )

    return {"success": True, "task_id": task_id, "new_status": new_status}


@router.post("/task", response_model=KanbanTask, status_code=201)
async def create_task(
    request: KanbanTaskCreate,
    db: DatabaseManager = Depends(get_db),
) -> KanbanTask:
    """Create a new kanban task."""
    # Generate ID from title
    task_id = request.title.lower().replace(" ", "-").replace("/", "-")[:60]

    # Check for duplicate
    result = db.execute("SELECT id FROM kanban_tasks WHERE id = ?", [task_id])
    if result.fetchone():
        raise HTTPException(status_code=409, detail=f"Task with id '{task_id}' already exists")

    db.execute(
        """INSERT INTO kanban_tasks (id, title, phase, priority, status, branch, depends_on, description, content, deadline)
           VALUES (?, ?, ?, ?, 'not_started', ?, ?, ?, ?, ?)""",
        [task_id, request.title, request.phase, request.priority, request.branch,
         request.depends_on, request.description, request.content, request.deadline],
    )

    result = db.execute("SELECT * FROM kanban_tasks WHERE id = ?", [task_id])
    col_names = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_task(row, col_names)


@router.patch("/task/{task_id}", response_model=KanbanTask)
async def update_task(
    task_id: str,
    request: KanbanTaskUpdate,
    db: DatabaseManager = Depends(get_db),
) -> KanbanTask:
    """Update a kanban task's fields."""
    result = db.execute("SELECT id FROM kanban_tasks WHERE id = ?", [task_id])
    if not result.fetchone():
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    updates = []
    values: list = []
    for field in ("title", "phase", "priority", "status", "branch", "depends_on", "description", "content", "deadline"):
        val = getattr(request, field, None)
        if val is not None:
            updates.append(f"{field} = ?")
            values.append(val)

    if request.status == "done":
        updates.append("completed_at = ?")
        values.append(datetime.now().isoformat())

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(task_id)
    db.execute(f"UPDATE kanban_tasks SET {', '.join(updates)} WHERE id = ?", values)

    result = db.execute("SELECT * FROM kanban_tasks WHERE id = ?", [task_id])
    col_names = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_task(row, col_names)


@router.delete("/task/{task_id}")
async def delete_task(
    task_id: str,
    db: DatabaseManager = Depends(get_db),
) -> dict:
    """Delete a kanban task."""
    result = db.execute("SELECT id FROM kanban_tasks WHERE id = ?", [task_id])
    if not result.fetchone():
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    db.execute("DELETE FROM kanban_tasks WHERE id = ?", [task_id])
    return {"success": True, "task_id": task_id}
