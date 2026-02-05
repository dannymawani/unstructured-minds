"""Extraction API endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..extraction import ExtractionPipeline
from ..middleware import limiter, validate_file_path, PathValidationError
from ..middleware.rate_limit import RATE_LIMIT_EXTRACTION
from ..middleware.validation import MAX_FILE_PATH_LENGTH
from ..storage import StorageBackend


router = APIRouter()


class ExtractRequest(BaseModel):
    """Request to extract data from a file."""

    file_path: str = Field(..., max_length=MAX_FILE_PATH_LENGTH)
    force: bool = False  # Force re-extraction even if already processed
    schema_name: Optional[str] = Field(
        None,
        max_length=50,
        description="Schema name to use for extraction (default: combined)",
    )


class ExtractResponse(BaseModel):
    """Response from extraction."""

    success: bool
    file_path: str
    message: str
    records_inserted: Optional[dict[str, int]] = None
    data: Optional[dict[str, Any]] = None


class ExtractBatchRequest(BaseModel):
    """Request to extract data from multiple files."""

    file_paths: list[str] = Field(..., max_length=50)  # Limit batch size
    force: bool = False
    schema_name: Optional[str] = Field(
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
@limiter.limit(RATE_LIMIT_EXTRACTION)
async def extract_file(
    request: ExtractRequest,
    http_request: Request,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude: ClaudeClient = Depends(get_claude),
) -> ExtractResponse:
    """Extract structured data from a markdown file.

    Args:
        request: Extraction request with file path
        http_request: HTTP request for rate limiting
        db: Database manager
        storage: Storage backend
        claude: Claude client

    Returns:
        Extraction result
    """
    # Validate file path
    try:
        validate_file_path(request.file_path)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Read file content
    try:
        content_bytes = await storage.read(request.file_path)
        content = content_bytes.decode("utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
    except ValueError as e:
        # Path traversal caught by storage backend
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

    # Run extraction
    pipeline = ExtractionPipeline(db, claude)
    result = await pipeline.extract(
        request.file_path,
        content,
        force=request.force,
        schema_name=request.schema_name,
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
    request: ExtractBatchRequest,
    http_request: Request,
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude: ClaudeClient = Depends(get_claude),
) -> ExtractBatchResponse:
    """Extract structured data from multiple files.

    Args:
        request: Batch extraction request
        http_request: HTTP request for rate limiting
        db: Database manager
        storage: Storage backend
        claude: Claude client

    Returns:
        Batch extraction results
    """
    # Validate all file paths first
    for file_path in request.file_paths:
        try:
            validate_file_path(file_path)
        except PathValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid path '{file_path}': {str(e)}")

    pipeline = ExtractionPipeline(db, claude)
    results = []
    successful = 0
    failed = 0

    for file_path in request.file_paths:
        try:
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")
            result = await pipeline.extract(
                file_path,
                content,
                force=request.force,
                schema_name=request.schema_name,
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
        total=len(request.file_paths),
        successful=successful,
        failed=failed,
        results=results,
    )
