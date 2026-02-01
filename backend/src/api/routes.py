"""API routes."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..db import DatabaseManager
from ..storage import StorageBackend

router = APIRouter()


# =============================================================================
# Vault API Models
# =============================================================================


class FileInfo(BaseModel):
    """File information."""

    path: str
    name: str
    is_directory: bool


class FileListResponse(BaseModel):
    """Response for file listing."""

    files: list[FileInfo]


class FileContentResponse(BaseModel):
    """Response for file content."""

    path: str
    content: str


class FileWriteRequest(BaseModel):
    """Request to write a file."""

    path: str
    content: str


class FileWriteResponse(BaseModel):
    """Response for file write."""

    path: str
    success: bool


class FileDeleteResponse(BaseModel):
    """Response for file deletion."""

    path: str
    success: bool


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


# =============================================================================
# Vault API Endpoints
# =============================================================================


@router.get("/vault/files", response_model=FileListResponse)
async def list_files(
    prefix: str = Query("", description="Path prefix to filter files"),
    storage: StorageBackend = Depends(get_storage),
) -> FileListResponse:
    """List files in the vault.

    Args:
        prefix: Optional path prefix to filter files

    Returns:
        List of files matching the prefix
    """
    try:
        file_paths = await storage.list(prefix)
        files = []
        seen_dirs: set[str] = set()

        for path in sorted(file_paths):
            # Get relative parts
            parts = path.split("/")

            # If there's a prefix, only include files under it
            if prefix:
                # Add directories
                for i in range(len(parts) - 1):
                    dir_path = "/".join(parts[: i + 1])
                    if dir_path not in seen_dirs and dir_path.startswith(prefix):
                        seen_dirs.add(dir_path)
                        files.append(
                            FileInfo(
                                path=dir_path,
                                name=parts[i],
                                is_directory=True,
                            )
                        )
            else:
                # Add top-level directories
                if len(parts) > 1:
                    dir_path = parts[0]
                    if dir_path not in seen_dirs:
                        seen_dirs.add(dir_path)
                        files.append(
                            FileInfo(
                                path=dir_path,
                                name=parts[0],
                                is_directory=True,
                            )
                        )

            # Add the file itself
            files.append(
                FileInfo(
                    path=path,
                    name=parts[-1],
                    is_directory=False,
                )
            )

        return FileListResponse(files=files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vault/file", response_model=FileContentResponse)
async def read_file(
    path: str = Query(..., description="Path to the file"),
    storage: StorageBackend = Depends(get_storage),
) -> FileContentResponse:
    """Read a file from the vault.

    Args:
        path: Path to the file

    Returns:
        File content as string
    """
    try:
        content = await storage.read(path)
        return FileContentResponse(path=path, content=content.decode("utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/file", response_model=FileWriteResponse)
async def write_file(
    request: FileWriteRequest,
    storage: StorageBackend = Depends(get_storage),
) -> FileWriteResponse:
    """Write a file to the vault.

    Args:
        request: File path and content

    Returns:
        Success status
    """
    try:
        await storage.write(request.path, request.content.encode("utf-8"))
        return FileWriteResponse(path=request.path, success=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vault/file", response_model=FileDeleteResponse)
async def delete_file(
    path: str = Query(..., description="Path to the file"),
    storage: StorageBackend = Depends(get_storage),
) -> FileDeleteResponse:
    """Delete a file from the vault.

    Args:
        path: Path to the file

    Returns:
        Success status
    """
    try:
        await storage.delete(path)
        return FileDeleteResponse(path=path, success=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
