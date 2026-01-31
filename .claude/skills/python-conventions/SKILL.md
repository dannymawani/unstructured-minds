---
name: python-conventions
description: Python and FastAPI coding conventions for the backend. Use when implementing or reviewing Python code.
user-invocable: false
---

# Python Conventions

Standards for the Unstructured Minds Python backend.

## Project Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Settings (pydantic-settings)
│   ├── claude/              # AI integration
│   │   ├── client.py        # Anthropic SDK wrapper
│   │   └── extraction.py    # Data extraction logic
│   ├── db/                  # Database layer
│   │   ├── connection.py    # DuckDB connection pool
│   │   └── queries.py       # SQL query functions
│   ├── api/                 # REST endpoints
│   │   ├── routes/
│   │   └── models.py        # Pydantic models
│   └── storage/             # File storage abstraction
├── tests/
└── pyproject.toml
```

## Type Hints

Always use type hints for function signatures:

```python
from typing import Optional, Annotated
from datetime import date

async def extract_exercises(
    content: str,
    note_date: date,
    client: AnthropicClient,
) -> list[ExerciseLog]:
    """Extract exercise data from note content."""
    ...
```

## Configuration

Use pydantic-settings for configuration:

```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    database_path: str = ".unstructured/unstructured.duckdb"
    vault_path: str = "./vault"

    class Config:
        env_file = ".env"

settings = Settings()
```

## Error Handling

```python
from fastapi import HTTPException, status

class NoteNotFoundError(Exception):
    """Raised when a note is not found."""
    pass

class ExtractionError(Exception):
    """Raised when data extraction fails."""
    pass

# In routes
@router.get("/notes/{note_id}")
async def get_note(note_id: str, db: DB):
    try:
        note = await db.get_note(note_id)
    except NoteNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found"
        )
    return note
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

async def process_note(note_path: str):
    logger.info(f"Processing note: {note_path}")
    try:
        result = await extract_data(note_path)
        logger.debug(f"Extracted {len(result)} items")
    except Exception as e:
        logger.error(f"Failed to process {note_path}: {e}")
        raise
```

## Testing

```python
# tests/test_extraction.py
import pytest
from src.claude.extraction import extract_exercises

@pytest.fixture
def sample_note_content():
    return """
    ## Training
    Did squats 3x5 at 100kg, felt good.
    """

async def test_extract_exercises(sample_note_content):
    result = await extract_exercises(sample_note_content, date(2026, 1, 15))
    assert len(result) == 1
    assert result[0].exercise_name == "Squat"
    assert result[0].weight_kg == 100
```

## DuckDB Operations

```python
import duckdb
from contextlib import contextmanager

@contextmanager
def get_db_connection(path: str):
    conn = duckdb.connect(path)
    try:
        yield conn
    finally:
        conn.close()

def insert_exercises(conn: duckdb.DuckDBPyConnection, exercises: list[dict]):
    conn.executemany(
        """
        INSERT INTO exercise_log (activity_id, date, activity_type, exercise_name, sets, reps, weight_kg)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(e["activity_id"], e["date"], e["activity_type"],
          e["exercise_name"], e["sets"], e["reps"], e["weight_kg"])
         for e in exercises]
    )
```
