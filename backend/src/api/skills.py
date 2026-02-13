"""Skills API endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..skills import SkillContext, SkillRegistry, get_default_registry
from ..storage import StorageBackend
from .dependencies import get_storage as _dep_get_storage


router = APIRouter()


class SkillInfo(BaseModel):
    """Information about a skill."""

    name: str
    description: str


class SkillListResponse(BaseModel):
    """Response listing available skills."""

    skills: list[SkillInfo]


class SkillExecuteRequest(BaseModel):
    """Request to execute a skill."""

    skill: str
    date: Optional[str] = None  # Optional date parameter (YYYY-MM-DD)
    input: Optional[str] = None  # Optional user input


class SkillExecuteResponse(BaseModel):
    """Response from skill execution."""

    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
    file_path: Optional[str] = None


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend (user-scoped in cloud mode)."""
    return _dep_get_storage(request)


def get_skill_registry() -> SkillRegistry:
    """Get skill registry."""
    return get_default_registry()


@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SkillListResponse:
    """List all available skills.

    Returns:
        List of skill names and descriptions
    """
    skills = registry.list()
    return SkillListResponse(
        skills=[SkillInfo(name=s["name"], description=s["description"]) for s in skills]
    )


@router.post("/skills/execute", response_model=SkillExecuteResponse)
async def execute_skill(
    request: SkillExecuteRequest,
    storage: StorageBackend = Depends(get_storage),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SkillExecuteResponse:
    """Execute a skill.

    Args:
        request: Skill execution request
        storage: Storage backend for file operations
        registry: Skill registry

    Returns:
        Skill execution result
    """
    context = SkillContext(
        storage=storage,
        current_date=request.date,
        user_input=request.input,
    )

    try:
        result = await registry.execute(request.skill, context)
        return SkillExecuteResponse(
            success=result.success,
            message=result.message,
            data=result.data,
            file_path=result.file_path,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill execution failed: {str(e)}")
