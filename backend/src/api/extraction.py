"""Extraction API endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..extraction import ExtractionPipeline
from ..storage import StorageBackend


router = APIRouter()


class ExtractRequest(BaseModel):
    """Request to extract data from a file."""

    file_path: str
    force: bool = False  # Force re-extraction even if already processed


class ExtractResponse(BaseModel):
    """Response from extraction."""

    success: bool
    file_path: str
    message: str
    records_inserted: Optional[dict[str, int]] = None
    data: Optional[dict[str, Any]] = None


class ExtractBatchRequest(BaseModel):
    """Request to extract data from multiple files."""

    file_paths: list[str]
    force: bool = False


class ExtractBatchResponse(BaseModel):
    """Response from batch extraction."""

    total: int
    successful: int
    failed: int
    results: list[ExtractResponse]


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend from app state."""
    return request.app.state.storage


def get_claude(request: Request) -> ClaudeClient:
    """Get Claude client from app state."""
    return request.app.state.claude


@router.post("/extract", response_model=ExtractResponse)
async def extract_file(
    request: ExtractRequest,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude: ClaudeClient = Depends(get_claude),
) -> ExtractResponse:
    """Extract structured data from a markdown file.

    Args:
        request: Extraction request with file path
        db: Database manager
        storage: Storage backend
        claude: Claude client

    Returns:
        Extraction result
    """
    # Read file content
    try:
        content_bytes = await storage.read(request.file_path)
        content = content_bytes.decode("utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    # Run extraction
    pipeline = ExtractionPipeline(db, claude)
    result = await pipeline.extract(request.file_path, content, force=request.force)

    return ExtractResponse(
        success=result.success,
        file_path=result.file_path,
        message=result.error or "Extraction complete",
        records_inserted=result.records_inserted if result.success else None,
        data=result.data,
    )


@router.post("/extract/batch", response_model=ExtractBatchResponse)
async def extract_batch(
    request: ExtractBatchRequest,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude: ClaudeClient = Depends(get_claude),
) -> ExtractBatchResponse:
    """Extract structured data from multiple files.

    Args:
        request: Batch extraction request
        db: Database manager
        storage: Storage backend
        claude: Claude client

    Returns:
        Batch extraction results
    """
    pipeline = ExtractionPipeline(db, claude)
    results = []
    successful = 0
    failed = 0

    for file_path in request.file_paths:
        try:
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")
            result = await pipeline.extract(file_path, content, force=request.force)

            if result.success:
                successful += 1
            else:
                failed += 1

            results.append(
                ExtractResponse(
                    success=result.success,
                    file_path=result.file_path,
                    message=result.error or "Extraction complete",
                    records_inserted=result.records_inserted if result.success else None,
                )
            )
        except FileNotFoundError:
            failed += 1
            results.append(
                ExtractResponse(
                    success=False,
                    file_path=file_path,
                    message=f"File not found: {file_path}",
                )
            )
        except Exception as e:
            failed += 1
            results.append(
                ExtractResponse(
                    success=False,
                    file_path=file_path,
                    message=f"Error: {str(e)}",
                )
            )

    return ExtractBatchResponse(
        total=len(request.file_paths),
        successful=successful,
        failed=failed,
        results=results,
    )
