---
name: api-conventions
description: API design conventions for FastAPI backend. Use when implementing or reviewing API endpoints.
user-invocable: false
---

# API Conventions

Standards for the Unstructured Minds FastAPI backend.

## Endpoint Structure

```
/api/v1/{resource}          # Collection
/api/v1/{resource}/{id}     # Single item
/api/v1/{resource}/{id}/{sub-resource}  # Nested
```

## HTTP Methods

| Method | Purpose | Success Code | Error Codes |
|--------|---------|--------------|-------------|
| GET    | Retrieve | 200 | 404, 400 |
| POST   | Create | 201 | 400, 422 |
| PUT    | Full update | 200 | 404, 400, 422 |
| PATCH  | Partial update | 200 | 404, 400, 422 |
| DELETE | Remove | 204 | 404 |

## Request/Response Models

Use Pydantic models for all request bodies and responses:

```python
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class NoteCreate(BaseModel):
    """Request model for creating a note."""
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    date: date

class NoteResponse(BaseModel):
    """Response model for a note."""
    id: str
    title: str
    content: str
    date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

## Error Response Format

```python
from fastapi import HTTPException

class ErrorResponse(BaseModel):
    detail: str
    code: str  # Machine-readable error code
    field: Optional[str] = None  # For validation errors

# Usage
raise HTTPException(
    status_code=404,
    detail={"detail": "Note not found", "code": "NOTE_NOT_FOUND"}
)
```

## Pagination

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool

@router.get("/notes", response_model=PaginatedResponse[NoteResponse])
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    ...
```

## Dependency Injection

```python
from fastapi import Depends
from typing import Annotated

async def get_db() -> AsyncGenerator[DuckDBConnection, None]:
    conn = await connect_db()
    try:
        yield conn
    finally:
        await conn.close()

DB = Annotated[DuckDBConnection, Depends(get_db)]

@router.get("/notes/{note_id}")
async def get_note(note_id: str, db: DB):
    ...
```

## Async Operations

- Use `async def` for all route handlers
- Use async database operations
- Use `asyncio.gather()` for parallel operations
