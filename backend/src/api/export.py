"""Export and Import API endpoints."""

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import settings
from ..db import DatabaseManager, get_table_names
from ..db.sql_compat import get_dialect
from .dependencies import get_db as _dep_get_db
from ..middleware import limiter, validate_file_size, FileSizeError
from ..middleware.rate_limit import RATE_LIMIT_IMPORT
from ..middleware.validation import MAX_FILE_SIZE_BYTES, sanitize_sql_identifier
from ..storage import StorageBackend


router = APIRouter(prefix="/export", tags=["export"])


class ExportDataResponse(BaseModel):
    """Response for data export info."""

    tables: list[str]
    format: str


class ImportResponse(BaseModel):
    """Response for import operation."""

    success: bool
    message: str
    files_imported: int
    extraction_triggered: bool


def get_db(request: Request):
    """Get database manager from app state."""
    return _dep_get_db(request)


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend from app state."""
    return request.app.state.storage


async def _create_vault_zip(storage: StorageBackend) -> io.BytesIO:
    """Create a ZIP archive of the vault using StorageBackend.

    Works with both local filesystem and Postgres storage.

    Returns:
        BytesIO buffer containing ZIP file
    """
    buffer = io.BytesIO()

    files = await storage.list("")

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            content = await storage.read(file_path)
            zf.writestr(file_path, content)

    buffer.seek(0)
    return buffer


def _export_table_to_csv(db: DatabaseManager, table_name: str) -> str:
    """Export a table to CSV format.

    Args:
        db: Database manager
        table_name: Name of table to export

    Returns:
        CSV string

    Raises:
        ValueError: If table name is invalid
    """
    # Sanitize table name to prevent SQL injection
    safe_table_name = sanitize_sql_identifier(table_name)
    result = db.execute(f"SELECT * FROM {safe_table_name}")
    rows = result.fetchall()
    columns = [desc[0] for desc in result.description]

    # Build CSV manually to handle None values properly
    lines = [",".join(columns)]
    for row in rows:
        values = []
        for val in row:
            if val is None:
                values.append("")
            elif isinstance(val, str):
                # Escape quotes and wrap in quotes if contains comma or quote
                escaped = val.replace('"', '""')
                if "," in val or '"' in val or "\n" in val:
                    values.append(f'"{escaped}"')
                else:
                    values.append(escaped)
            else:
                values.append(str(val))
        lines.append(",".join(values))

    return "\n".join(lines)


def _export_table_to_json(db: DatabaseManager, table_name: str) -> list[dict]:
    """Export a table to JSON format.

    Args:
        db: Database manager
        table_name: Name of table to export

    Returns:
        List of row dictionaries

    Raises:
        ValueError: If table name is invalid
    """
    # Sanitize table name to prevent SQL injection
    safe_table_name = sanitize_sql_identifier(table_name)
    result = db.execute(f"SELECT * FROM {safe_table_name}")
    rows = result.fetchall()
    columns = [desc[0] for desc in result.description]

    data = []
    for row in rows:
        row_dict = {}
        for col, val in zip(columns, row):
            # Convert datetime objects to ISO strings
            if hasattr(val, "isoformat"):
                row_dict[col] = val.isoformat()
            else:
                row_dict[col] = val
        data.append(row_dict)

    return data


@router.get("/vault")
async def export_vault(
    storage: StorageBackend = Depends(get_storage),
) -> StreamingResponse:
    """Export vault as a ZIP file.

    Returns all markdown files and other content from the vault directory.
    Works with both local filesystem and Postgres storage.
    """
    # Create ZIP archive using storage backend
    zip_buffer = await _create_vault_zip(storage)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"vault_export_{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/data")
async def export_data(
    format: Literal["csv", "json"] = "csv",
    db: DatabaseManager = Depends(get_db),
) -> StreamingResponse:
    """Export extracted data as CSV or JSON.

    Args:
        format: Export format (csv or json)

    Returns ZIP containing all tables in the specified format.
    """
    # Get all data tables (exclude extraction_log)
    if get_dialect(db) == "postgres":
        result = db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = [row[0] for row in result.fetchall()]
    else:
        if not db._conn:
            raise HTTPException(status_code=500, detail="Database not connected")
        tables = get_table_names(db._conn)

    data_tables = [t for t in tables if t != "extraction_log"]

    if not data_tables:
        raise HTTPException(status_code=404, detail="No data tables found")

    # Create ZIP archive with all tables
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for table_name in data_tables:
            try:
                if format == "csv":
                    content = _export_table_to_csv(db, table_name)
                    zf.writestr(f"{table_name}.csv", content)
                else:
                    data = _export_table_to_json(db, table_name)
                    content = json.dumps(data, indent=2, default=str)
                    zf.writestr(f"{table_name}.json", content)
            except Exception as e:
                # Skip tables that fail to export
                continue

    buffer.seek(0)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data_export_{timestamp}.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/data/tables")
async def list_export_tables(
    db: DatabaseManager = Depends(get_db),
) -> ExportDataResponse:
    """List available tables for export.

    Returns list of table names that can be exported.
    """
    if get_dialect(db) == "postgres":
        result = db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = [row[0] for row in result.fetchall()]
    else:
        if not db._conn:
            raise HTTPException(status_code=500, detail="Database not connected")
        tables = get_table_names(db._conn)

    data_tables = [t for t in tables if t != "extraction_log"]

    return ExportDataResponse(
        tables=data_tables,
        format="csv or json",
    )


# Import router
import_router = APIRouter(prefix="/import", tags=["import"])


@import_router.post("/vault", response_model=ImportResponse)
@limiter.limit(RATE_LIMIT_IMPORT)
async def import_vault(
    request: Request,
    file: UploadFile,
    trigger_extraction: bool = True,
    storage: StorageBackend = Depends(get_storage),
) -> ImportResponse:
    """Import vault files from a ZIP archive.

    Args:
        request: HTTP request for rate limiting
        file: ZIP file containing vault files
        trigger_extraction: Whether to trigger re-extraction after import

    Extracts ZIP contents to the vault directory.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="File must be a ZIP archive",
        )

    files_imported = 0

    try:
        # Read uploaded file
        content = await file.read()

        # Validate file size
        try:
            validate_file_size(len(content), MAX_FILE_SIZE_BYTES)
        except FileSizeError as e:
            raise HTTPException(status_code=413, detail=str(e))

        zip_buffer = io.BytesIO(content)

        with zipfile.ZipFile(zip_buffer, "r") as zf:
            # Security check: ensure no path traversal
            for name in zf.namelist():
                normalized = Path(name).as_posix()
                if normalized.startswith("/") or ".." in normalized:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid path in ZIP: {name}",
                    )

            # Extract files using storage backend
            for member in zf.infolist():
                if member.is_dir():
                    continue

                with zf.open(member) as src:
                    await storage.write(member.filename, src.read())
                    files_imported += 1

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Invalid ZIP file",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error importing vault: {str(e)}",
        )

    return ImportResponse(
        success=True,
        message=f"Successfully imported {files_imported} files",
        files_imported=files_imported,
        extraction_triggered=trigger_extraction,
    )


# Combine routers for easy inclusion
def include_export_routes(app):
    """Include export and import routes in the app."""
    app.include_router(router)
    app.include_router(import_router)
