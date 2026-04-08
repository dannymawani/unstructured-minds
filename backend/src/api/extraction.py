"""Extraction API endpoints."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..extraction import ExtractionPipeline
from ..middleware import PathValidationError, limiter, validate_file_path
from ..middleware.rate_limit import RATE_LIMIT_EXTRACTION
from ..middleware.validation import MAX_FILE_PATH_LENGTH
from ..storage import StorageBackend
from .dependencies import get_db as _dep_get_db
from .dependencies import get_storage as _dep_get_storage
from .dependencies import get_user_id

router = APIRouter()


class ExtractRequest(BaseModel):
    """Request to extract data from a file."""

    file_path: str = Field(..., max_length=MAX_FILE_PATH_LENGTH)
    force: bool = False  # Force re-extraction even if already processed
    schema_name: str | None = Field(
        None,
        max_length=50,
        description="Schema name to use for extraction (default: combined)",
    )


class ExtractResponse(BaseModel):
    """Response from extraction."""

    success: bool
    file_path: str
    message: str
    records_inserted: dict[str, int] | None = None
    data: dict[str, Any] | None = None


class ExtractAllRequest(BaseModel):
    """Request to extract all files in the vault."""

    force: bool = True  # Default true — this is for recovery
    schema_name: str | None = None
    exclude_prefixes: list[str] = ["Templates/"]


class ExtractBatchRequest(BaseModel):
    """Request to extract data from multiple files."""

    file_paths: list[str] = Field(..., max_length=50)  # Limit batch size
    force: bool = False
    schema_name: str | None = Field(
        None,
        max_length=50,
        description="Schema name to use for extraction (default: combined)",
    )


class ExtractBatchResponse(BaseModel):
    """Response from batch extraction."""

    total: int
    successful: int
    failed: int
    results: list[ExtractResponse]


def get_db(request: Request):
    """Get database manager from app state."""
    return _dep_get_db(request)


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend (user-scoped in cloud mode)."""
    return _dep_get_storage(request)


def get_claude(request: Request) -> ClaudeClient:
    """Get Claude client from app state."""
    return request.app.state.claude


@router.post("/extract", response_model=ExtractResponse)
@limiter.limit(RATE_LIMIT_EXTRACTION)
async def extract_file(
    request: Request,
    body: ExtractRequest,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude: ClaudeClient = Depends(get_claude),
    user_id: str = Depends(get_user_id),
) -> ExtractResponse:
    """Extract structured data from a markdown file.

    Args:
        request: HTTP request (required by slowapi rate limiter)
        body: Extraction request with file path
        db: Database manager
        storage: Storage backend
        claude: Claude client

    Returns:
        Extraction result
    """
    # Validate file path
    try:
        validate_file_path(body.file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Read file content
    try:
        content_bytes = await storage.read(body.file_path)
        content = content_bytes.decode("utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {body.file_path}")
    except ValueError as e:
        # Path traversal caught by storage backend
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    # Run extraction
    pipeline = ExtractionPipeline(db, claude, user_id=user_id)
    result = await pipeline.extract(
        body.file_path,
        content,
        force=body.force,
        schema_name=body.schema_name,
    )

    return ExtractResponse(
        success=result.success,
        file_path=result.file_path,
        message=result.error or "Extraction complete",
        records_inserted=result.records_inserted if result.success else None,
        data=result.data,
    )


@router.post("/extract/batch", response_model=ExtractBatchResponse)
@limiter.limit(RATE_LIMIT_EXTRACTION)
async def extract_batch(
    request: Request,
    body: ExtractBatchRequest,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude: ClaudeClient = Depends(get_claude),
    user_id: str = Depends(get_user_id),
) -> ExtractBatchResponse:
    """Extract structured data from multiple files.

    Args:
        request: HTTP request (required by slowapi rate limiter)
        body: Batch extraction request
        db: Database manager
        storage: Storage backend
        claude: Claude client

    Returns:
        Batch extraction results
    """
    # Validate all file paths first
    for file_path in body.file_paths:
        try:
            validate_file_path(file_path)
        except PathValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid path '{file_path}': {str(e)}")

    pipeline = ExtractionPipeline(db, claude, user_id=user_id)
    results = []
    successful = 0
    failed = 0

    for file_path in body.file_paths:
        try:
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")
            result = await pipeline.extract(
                file_path,
                content,
                force=body.force,
                schema_name=body.schema_name,
            )

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
        total=len(body.file_paths),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.post("/extract/all")
async def extract_all(
    request: Request,
    body: ExtractAllRequest,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude: ClaudeClient = Depends(get_claude),
    user_id: str = Depends(get_user_id),
) -> EventSourceResponse:
    """Re-extract all markdown files in the vault via SSE.

    Discovers all .md files, filters out excluded prefixes (e.g. Templates/),
    and runs each through the extraction pipeline. Streams progress as
    Server-Sent Events so callers can monitor without timeout.

    Usage:
        curl -N -X POST http://localhost:8000/extract/all \\
          -H "Content-Type: application/json" \\
          -d '{"force": true}'
    """
    all_files = await storage.list("")
    md_files = [
        f for f in all_files
        if f.endswith(".md")
        and not any(f.startswith(prefix) for prefix in body.exclude_prefixes)
    ]
    md_files.sort()

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        total = len(md_files)
        yield {"event": "start", "data": json.dumps({"total": total})}

        pipeline = ExtractionPipeline(db, claude, user_id=user_id)
        successful = 0
        failed = 0

        for i, file_path in enumerate(md_files):
            try:
                content_bytes = await storage.read(file_path)
                content = content_bytes.decode("utf-8")
                result = await pipeline.extract(
                    file_path,
                    content,
                    force=body.force,
                    schema_name=body.schema_name,
                )
                if result.success:
                    successful += 1
                    message = result.error or "Extraction complete"
                else:
                    failed += 1
                    message = result.error or "Extraction failed"

                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "file": file_path,
                        "success": result.success,
                        "message": message,
                        "records_inserted": result.records_inserted,
                        "index": i + 1,
                        "total": total,
                    }),
                }
            except Exception as e:
                failed += 1
                yield {
                    "event": "progress",
                    "data": json.dumps({
                        "file": file_path,
                        "success": False,
                        "message": str(e),
                        "records_inserted": None,
                        "index": i + 1,
                        "total": total,
                    }),
                }

        yield {
            "event": "done",
            "data": json.dumps({
                "total": total,
                "successful": successful,
                "failed": failed,
            }),
        }

    return EventSourceResponse(event_generator())
