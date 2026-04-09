"""API routes for vault file operations."""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..cache import file_list_cache, invalidate_all
from ..db import DatabaseManager
from ..middleware import PathValidationError, validate_file_path
from ..middleware.validation import MAX_FILE_PATH_LENGTH, MAX_QUERY_LENGTH
from ..storage import StorageBackend
from ..templates.daily_note import render_daily_note
from .dependencies import get_storage as _dep_get_storage
from .dependencies import get_user_id
from .settings import resolve_daily_note_path

logger = logging.getLogger(__name__)

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


class FileRenameRequest(BaseModel):
    """Request to rename a file."""

    old_path: str = Field(..., max_length=MAX_FILE_PATH_LENGTH)
    new_path: str = Field(..., max_length=MAX_FILE_PATH_LENGTH)


class FileRenameResponse(BaseModel):
    """Response for file rename."""

    old_path: str
    new_path: str
    success: bool


class QuickCaptureRequest(BaseModel):
    """Request for quick capture."""

    text: str = Field(..., min_length=1, max_length=10000)


class QuickCaptureResponse(BaseModel):
    """Response for quick capture."""

    success: bool
    path: str
    timestamp: str


async def _add_also_worked_on(
    storage: StorageBackend, file_path: str
) -> None:
    """Add a reference to a modified file in today's daily note.

    Appends to an '## Also worked on' section at the bottom of the daily note.
    Only adds if the file is not already referenced.
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    daily_path = resolve_daily_note_path(date_str)

    # Don't add self-references
    if file_path == daily_path:
        return

    # Check if daily note exists
    if not await storage.exists(daily_path):
        return

    try:
        content_bytes = await storage.read(daily_path)
        content = content_bytes.decode("utf-8")

        # Check if file is already referenced as a wikilink
        if f"[[{file_path}]]" in content:
            return

        # Find or create "Also worked on" section
        section_header = "## Also worked on"
        if section_header in content:
            # Append to existing section
            idx = content.index(section_header) + len(section_header)
            # Find end of line after header
            newline_idx = content.index("\n", idx) if "\n" in content[idx:] else len(content)
            entry = f"\n- [[{file_path}]]"
            content = content[:newline_idx] + entry + content[newline_idx:]
        else:
            # Add new section at end
            content = content.rstrip() + f"\n\n{section_header}\n- [[{file_path}]]\n"

        await storage.write(daily_path, content.encode("utf-8"))
    except Exception:
        logger.debug("Failed to update daily note with 'also worked on' reference", exc_info=True)


def _is_daily_note_path(file_path: str) -> bool:
    """Check if a file path looks like a daily note."""
    filename = file_path.split("/")[-1].replace(".md", "")
    clean_name = re.sub(r"-daily-note$", "", filename)
    try:
        datetime.strptime(clean_name, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend (user-scoped in cloud mode)."""
    return _dep_get_storage(request)


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
        cache_key = f"files:{prefix}"
        cached = file_list_cache.get(cache_key)
        if cached is not None:
            return cached

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
                # Add all intermediate directories
                for i in range(len(parts) - 1):
                    dir_path = "/".join(parts[: i + 1])
                    if dir_path not in seen_dirs:
                        seen_dirs.add(dir_path)
                        files.append(
                            FileInfo(
                                path=dir_path,
                                name=parts[i],
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

        response = FileListResponse(files=files)
        file_list_cache.set(cache_key, response)
        return response
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
    request: Request,
    body: FileWriteRequest,
    extract: bool = Query(True, description="Whether to trigger Claude extraction after save"),
    storage: StorageBackend = Depends(get_storage),
    user_id: str = Depends(get_user_id),
) -> FileWriteResponse:
    """Write a file to the vault.

    Args:
        body: File path and content
        extract: If False, save to disk only (no Claude extraction).
                 Used by autosave to avoid unnecessary API calls.

    Returns:
        Success status and whether extraction was triggered
    """
    # Validate path for security
    try:
        validate_file_path(body.path, allow_any_extension=True)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        await storage.write(body.path, body.content.encode("utf-8"))
        invalidate_all()

        # Only trigger extraction if requested
        did_extract = False
        if extract and body.path.endswith(".md"):
            try:
                claude = request.app.state.claude
                db = request.app.state.db
                if claude.is_configured:
                    from ..extraction import ExtractionPipeline
                    pipeline = ExtractionPipeline(db, claude, user_id=user_id)
                    result = await pipeline.extract(body.path, body.content)
                    did_extract = result.success

                    # Clean up demo data for the extracted date
                    if did_extract:
                        try:
                            from ..onboarding.lifecycle import cleanup_demo_for_date
                            extracted_date = pipeline._extract_date_from_path(body.path)
                            if extracted_date:
                                cleanup_demo_for_date(db, extracted_date, user_id)
                        except Exception:
                            pass  # Demo cleanup failure shouldn't fail the save
            except Exception:
                logger.exception("extraction_failed path=%s", body.path)

            # Add "also worked on" reference for non-daily-note files
            if not _is_daily_note_path(body.path):
                try:
                    await _add_also_worked_on(storage, body.path)
                except Exception:
                    pass

        return FileWriteResponse(path=body.path, success=True, extracted=did_extract)
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
        invalidate_all()

        return FileDeleteResponse(path=path, success=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/vault/file", response_model=FileRenameResponse)
async def rename_file(
    body: FileRenameRequest,
    storage: StorageBackend = Depends(get_storage),
) -> FileRenameResponse:
    """Rename a file in the vault.

    Args:
        body: Old and new file paths

    Returns:
        Success status with old and new paths
    """
    # Validate both paths for security
    try:
        validate_file_path(body.old_path, allow_any_extension=True)
        validate_file_path(body.new_path, allow_any_extension=True)
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        await storage.rename(body.old_path, body.new_path)
        invalidate_all()

        return FileRenameResponse(
            old_path=body.old_path, new_path=body.new_path, success=True
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"File not found: {body.old_path}"
        )
    except FileExistsError:
        raise HTTPException(
            status_code=409, detail=f"File already exists: {body.new_path}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Daily Note Migration Endpoint
# =============================================================================


class MigrateResponse(BaseModel):
    """Response for migration."""

    success: bool
    moved: int
    details: list[str]


@router.post("/vault/migrate-daily-notes", response_model=MigrateResponse)
async def migrate_daily_notes(
    storage: StorageBackend = Depends(get_storage),
) -> MigrateResponse:
    """Migrate daily notes from Daily-Notes/YYYY-MM/ to the configured template path.

    Moves files matching YYYY-MM-DD.md from the old structure to the new one.
    Also moves Life-Profile.md to root if found.
    """
    from .settings import get_daily_note_template

    get_daily_note_template()
    details: list[str] = []
    moved = 0

    try:
        all_files = await storage.list("Daily-Notes")
    except Exception:
        return MigrateResponse(success=True, moved=0, details=["No Daily-Notes directory found"])

    for file_path in all_files:
        if not file_path.endswith(".md"):
            continue

        filename = file_path.split("/")[-1]
        basename = filename.replace(".md", "")

        # Move date-based files to new template path
        try:
            datetime.strptime(basename, "%Y-%m-%d")
        except ValueError:
            # Non-date file (e.g. Life-Profile.md) — move to root
            new_path = filename
            try:
                if not await storage.exists(new_path):
                    await storage.rename(file_path, new_path)
                    details.append(f"{file_path} -> {new_path}")
                    moved += 1
            except Exception as e:
                details.append(f"Error moving {file_path}: {e}")
            continue

        # Date-based file — compute new path from template
        new_path = resolve_daily_note_path(basename)
        if new_path == file_path:
            continue

        try:
            if await storage.exists(new_path):
                details.append(f"Skipped {file_path} (target exists: {new_path})")
                continue
            await storage.rename(file_path, new_path)
            details.append(f"{file_path} -> {new_path}")
            moved += 1
        except Exception as e:
            details.append(f"Error moving {file_path}: {e}")

    invalidate_all()
    return MigrateResponse(success=True, moved=moved, details=details)


# =============================================================================
# Quick Capture Endpoint
# =============================================================================



@router.post("/vault/quick-capture", response_model=QuickCaptureResponse)
async def quick_capture(
    request: QuickCaptureRequest,
    storage: StorageBackend = Depends(get_storage),
) -> QuickCaptureResponse:
    """Quick capture - append text to today's daily note.

    Appends the text with a timestamp to the Adhoc Notes section
    of today's daily note. Creates the daily note if it doesn't exist.

    Args:
        request: Quick capture text

    Returns:
        Success status with path and timestamp
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # Build the file path using configurable template
    file_path = resolve_daily_note_path(date_str)

    # Format the quick note entry
    quick_note_entry = f"- {time_str} - {request.text}"

    try:
        # Check if daily note exists
        if await storage.exists(file_path):
            # Read existing content
            content_bytes = await storage.read(file_path)
            content = content_bytes.decode("utf-8")

            # Find the Adhoc Notes section and append to it
            adhoc_pattern = r"(## .*Adhoc Notes\n)"
            match = re.search(adhoc_pattern, content)

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
                        + "\n\n## 📝 Adhoc Notes\n"
                        + quick_note_entry
                        + "\n"
                        + content[insert_pos:]
                    )
                else:
                    # No frontmatter, prepend
                    new_content = (
                        "## 📝 Adhoc Notes\n" + quick_note_entry + "\n\n" + content
                    )

            await storage.write(file_path, new_content.encode("utf-8"))
        else:
            # Create new daily note from vault template (or hardcoded fallback)
            try:
                tpl_bytes = await storage.read("Templates/daily.md")
                content = tpl_bytes.decode("utf-8")
            except Exception:
                content = render_daily_note()
            # Insert quick note entry under the Adhoc Notes section
            adhoc_match = re.search(r"(## .*Adhoc Notes\n)", content)
            if adhoc_match:
                insert_pos = adhoc_match.end()
                content = (
                    content[:insert_pos] + quick_note_entry + "\n" + content[insert_pos:]
                )
            await storage.write(file_path, content.encode("utf-8"))

        return QuickCaptureResponse(
            success=True,
            path=file_path,
            timestamp=time_str,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
