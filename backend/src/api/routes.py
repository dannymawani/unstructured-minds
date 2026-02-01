"""API routes."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..db import DatabaseManager
from ..storage import StorageBackend

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: str
    claude_enabled: bool


class StatusResponse(BaseModel):
    """System status response."""

    status: str
    database: str
    storage: str
    vault_path: str
    data_path: str


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend from app state."""
    return request.app.state.storage


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        claude_enabled=settings.claude_enabled,
    )


@router.get("/status", response_model=StatusResponse)
async def status(
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> StatusResponse:
    """System status endpoint."""
    # Check database connectivity
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "error"

    # Check storage accessibility
    try:
        await storage.exists("")
        storage_status = "connected"
    except Exception:
        storage_status = "error"

    return StatusResponse(
        status="ok" if db_status == "connected" and storage_status == "connected" else "degraded",
        database=db_status,
        storage=storage_status,
        vault_path=str(settings.vault_path.absolute()),
        data_path=str(settings.data_path.absolute()),
    )
