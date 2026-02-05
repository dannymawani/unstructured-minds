"""Kanban API endpoints for reading task files from the kanban folder."""

import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/kanban", tags=["kanban"])

# Path to kanban folder relative to project root
KANBAN_BASE = Path(__file__).parent.parent.parent.parent / "implementation_plan" / "kanban"


class KanbanTask(BaseModel):
    """A single kanban task."""

    id: str
    filename: str
    title: str
    phase: Optional[str] = None
    priority: Optional[str] = None
    status: str
    description: Optional[str] = None
    content: str


class KanbanColumn(BaseModel):
    """A kanban column with tasks."""

    name: str
    tasks: list[KanbanTask]


class KanbanBoard(BaseModel):
    """Full kanban board with all columns."""

    columns: list[KanbanColumn]


def parse_task_file(filepath: Path, status: str) -> KanbanTask:
    """Parse a markdown task file into a KanbanTask."""
    content = filepath.read_text()

    # Extract title from first H1
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else filepath.stem

    # Extract phase
    phase_match = re.search(r"\*\*Phase:\*\*\s*(.+)", content)
    phase = phase_match.group(1).strip() if phase_match else None

    # Extract priority
    priority_match = re.search(r"\*\*Priority:\*\*\s*(.+)", content)
    priority = priority_match.group(1).strip() if priority_match else None

    # Extract description (first paragraph after title)
    desc_match = re.search(r"## Description\n\n(.+?)(?:\n\n|\Z)", content, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else None

    return KanbanTask(
        id=filepath.stem,
        filename=filepath.name,
        title=title,
        phase=phase,
        priority=priority,
        status=status,
        description=description,
        content=content,
    )


def get_tasks_in_folder(folder: Path, status: str) -> list[KanbanTask]:
    """Get all tasks from a folder."""
    tasks = []
    if folder.exists():
        for filepath in sorted(folder.glob("*.md")):
            try:
                task = parse_task_file(filepath, status)
                tasks.append(task)
            except Exception as e:
                print(f"Error parsing {filepath}: {e}")
    return tasks


@router.get("/board", response_model=KanbanBoard)
async def get_kanban_board() -> KanbanBoard:
    """Get the full kanban board with all columns."""
    columns = [
        KanbanColumn(
            name="Not Started",
            tasks=get_tasks_in_folder(KANBAN_BASE / "not_started", "not_started"),
        ),
        KanbanColumn(
            name="In Progress",
            tasks=get_tasks_in_folder(KANBAN_BASE / "in_progress", "in_progress"),
        ),
        KanbanColumn(
            name="Done",
            tasks=get_tasks_in_folder(KANBAN_BASE / "done", "done"),
        ),
    ]
    return KanbanBoard(columns=columns)


@router.get("/task/{task_id}", response_model=KanbanTask)
async def get_task(task_id: str) -> KanbanTask:
    """Get a specific task by ID."""
    for status_folder in ["not_started", "in_progress", "done"]:
        folder = KANBAN_BASE / status_folder
        filepath = folder / f"{task_id}.md"
        if filepath.exists():
            return parse_task_file(filepath, status_folder)

    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.post("/task/{task_id}/move")
async def move_task(task_id: str, new_status: str) -> dict:
    """Move a task to a different status column."""
    if new_status not in ["not_started", "in_progress", "done"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    # Find the task
    source_path = None
    for status_folder in ["not_started", "in_progress", "done"]:
        folder = KANBAN_BASE / status_folder
        filepath = folder / f"{task_id}.md"
        if filepath.exists():
            source_path = filepath
            break

    if not source_path:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Move the file
    dest_folder = KANBAN_BASE / new_status
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_path = dest_folder / source_path.name

    # Update status in file content
    content = source_path.read_text()
    content = re.sub(
        r"\*\*Status:\*\*\s*.+",
        f"**Status:** {new_status.replace('_', ' ').title()}",
        content,
    )
    dest_path.write_text(content)

    # Remove old file if different location
    if source_path != dest_path:
        source_path.unlink()

    return {"success": True, "task_id": task_id, "new_status": new_status}
