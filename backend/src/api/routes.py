"""API routes for vault file operations."""

import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import DatabaseManager
from ..middleware import validate_file_path, PathValidationError
from ..middleware.validation import MAX_FILE_PATH_LENGTH, MAX_QUERY_LENGTH
from ..storage import StorageBackend
from ..webhooks import dispatch_event, WebhookEvent

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

    path: str = Field(..., max_length=MAX_FILE_PATH_LENGTH)
    content: str = Field(..., max_length=MAX_QUERY_LENGTH * 10)  # 100KB max


class FileWriteResponse(BaseModel):
    """Response for file write."""

    path: str
    success: bool
    extracted: bool = False


class FileDeleteResponse(BaseModel):
    """Response for file deletion."""

    path: str
    success: bool


class QuickCaptureRequest(BaseModel):
    """Request for quick capture."""

    text: str = Field(..., min_length=1, max_length=10000)


class QuickCaptureResponse(BaseModel):
    """Response for quick capture."""

    success: bool
    path: str
    timestamp: str


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend from app state."""
    return request.app.state.storage


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
    path: str = Query(..., description="Path to the file", max_length=MAX_FILE_PATH_LENGTH),
    storage: StorageBackend = Depends(get_storage),
) -> FileContentResponse:
    """Read a file from the vault.

    Args:
        path: Path to the file

    Returns:
        File content as string
    """
    # Validate path for security
    try:
        validate_file_path(path, allow_any_extension=True)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        content = await storage.read(path)
        return FileContentResponse(path=path, content=content.decode("utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        # Path traversal caught by storage
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/file", response_model=FileWriteResponse)
async def write_file(
    request_obj: Request,
    request: FileWriteRequest,
    extract: bool = Query(True, description="Whether to trigger Claude extraction after save"),
    storage: StorageBackend = Depends(get_storage),
) -> FileWriteResponse:
    """Write a file to the vault.

    Args:
        request: File path and content
        extract: If False, save to disk only (no Claude extraction).
                 Used by autosave to avoid unnecessary API calls.

    Returns:
        Success status and whether extraction was triggered
    """
    # Validate path for security
    try:
        validate_file_path(request.path, allow_any_extension=True)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Check if file exists to determine create vs update
        is_new = not await storage.exists(request.path)
        await storage.write(request.path, request.content.encode("utf-8"))

        # Dispatch webhook event
        event = WebhookEvent.NOTE_CREATED if is_new else WebhookEvent.NOTE_UPDATED
        await dispatch_event(
            event.value,
            {
                "path": request.path,
                "content_length": len(request.content),
            },
        )

        # Check if this is a daily note creation
        if is_new and "Daily-Notes/" in request.path:
            await dispatch_event(
                WebhookEvent.DAILY_CREATED.value,
                {
                    "path": request.path,
                    "content_length": len(request.content),
                },
            )

        # Only trigger extraction if requested
        did_extract = False
        if extract and request.path.endswith(".md"):
            try:
                claude = request_obj.app.state.claude
                db = request_obj.app.state.db
                if claude.is_configured:
                    from ..extraction import ExtractionPipeline
                    pipeline = ExtractionPipeline(db, claude)
                    result = await pipeline.extract(request.path, request.content)
                    did_extract = result.success
            except Exception:
                pass  # Extraction failure shouldn't fail the save

        return FileWriteResponse(path=request.path, success=True, extracted=did_extract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vault/file", response_model=FileDeleteResponse)
async def delete_file(
    path: str = Query(..., description="Path to the file", max_length=MAX_FILE_PATH_LENGTH),
    storage: StorageBackend = Depends(get_storage),
) -> FileDeleteResponse:
    """Delete a file from the vault.

    Args:
        path: Path to the file

    Returns:
        Success status
    """
    # Validate path for security
    try:
        validate_file_path(path, allow_any_extension=True)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        await storage.delete(path)

        # Dispatch webhook event for deletion
        await dispatch_event(
            WebhookEvent.NOTE_DELETED.value,
            {"path": path},
        )

        return FileDeleteResponse(path=path, success=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Quick Capture Endpoint
# =============================================================================

# Daily note template for quick capture (minimal version)
QUICK_CAPTURE_DAILY_NOTE_TEMPLATE = """---
date: {date}
type: daily-note
tags:
  - daily
  - journal
---

## Quick Notes

{quick_note}

---
**Previous**: [[{prev_date}]] | **Next**: [[{next_date}]]
"""


@router.post("/vault/quick-capture", response_model=QuickCaptureResponse)
async def quick_capture(
    request: QuickCaptureRequest,
    storage: StorageBackend = Depends(get_storage),
) -> QuickCaptureResponse:
    """Quick capture - append text to today's daily note.

    Appends the text with a timestamp to the "## Quick Notes" section
    of today's daily note. Creates the daily note if it doesn't exist.

    Args:
        request: Quick capture text

    Returns:
        Success status with path and timestamp
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    year_month = now.strftime("%Y-%m")
    prev_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    next_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # Build the file path: Daily-Notes/YYYY-MM/YYYY-MM-DD.md
    file_path = f"Daily-Notes/{year_month}/{date_str}.md"

    # Format the quick note entry
    quick_note_entry = f"- {time_str} - {request.text}"

    try:
        # Check if daily note exists
        if await storage.exists(file_path):
            # Read existing content
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")

            # Find the "## Quick Notes" section and append to it
            quick_notes_pattern = r"(## Quick Notes\n)"
            match = re.search(quick_notes_pattern, content)

            if match:
                # Insert the new entry after the section header
                insert_pos = match.end()
                new_content = (
                    content[:insert_pos] + quick_note_entry + "\n" + content[insert_pos:]
                )
            else:
                # Section doesn't exist, add it after frontmatter
                # Find end of frontmatter (second ---)
                frontmatter_end = content.find("---", content.find("---") + 3)
                if frontmatter_end != -1:
                    insert_pos = frontmatter_end + 3
                    new_content = (
                        content[:insert_pos]
                        + "\n\n## Quick Notes\n"
                        + quick_note_entry
                        + "\n"
                        + content[insert_pos:]
                    )
                else:
                    # No frontmatter, prepend
                    new_content = (
                        "## Quick Notes\n" + quick_note_entry + "\n\n" + content
                    )

            await storage.write(file_path, new_content.encode("utf-8"))
        else:
            # Create new daily note with the quick capture
            content = QUICK_CAPTURE_DAILY_NOTE_TEMPLATE.format(
                date=date_str,
                quick_note=quick_note_entry,
                prev_date=prev_date,
                next_date=next_date,
            )
            await storage.write(file_path, content.encode("utf-8"))

            # Dispatch webhook events for new daily note
            await dispatch_event(
                WebhookEvent.NOTE_CREATED.value,
                {"path": file_path, "content_length": len(content)},
            )
            await dispatch_event(
                WebhookEvent.DAILY_CREATED.value,
                {"path": file_path, "date": date_str},
            )

        return QuickCaptureResponse(
            success=True,
            path=file_path,
            timestamp=time_str,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
