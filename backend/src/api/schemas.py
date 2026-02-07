"""Schema management API endpoints."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

from ..config import settings
from ..extraction.schemas import EXTRACTION_SCHEMAS


router = APIRouter(prefix="/schemas", tags=["schemas"])


# Schema storage directory
SCHEMAS_DIR = settings.data_path / "schemas"


# =============================================================================
# Pydantic Models
# =============================================================================


class SchemaField(BaseModel):
    """Definition of a single field in a custom schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Field name")
    type: str = Field(
        ...,
        description="Field type: string, integer, number, boolean, array",
    )
    required: bool = Field(default=False, description="Whether the field is required")
    description: Optional[str] = Field(
        None, max_length=500, description="Field description"
    )
    min: Optional[float] = Field(None, description="Minimum value (for numbers)")
    max: Optional[float] = Field(None, description="Maximum value (for numbers)")
    enum: Optional[list[str]] = Field(
        None, description="Allowed values (for string enums)"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed_types = {"string", "integer", "number", "boolean", "array"}
        if v not in allowed_types:
            raise ValueError(f"Type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Only allow alphanumeric and underscores
        import re

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Field name must start with a letter and contain only letters, numbers, and underscores"
            )
        return v


class SchemaDefinition(BaseModel):
    """Definition of a custom extraction schema."""

    name: str = Field(
        ..., min_length=1, max_length=50, description="Schema name (unique identifier)"
    )
    description: str = Field(
        ..., min_length=1, max_length=500, description="Schema description"
    )
    fields: list[SchemaField] = Field(
        ..., min_length=1, max_length=50, description="List of fields to extract"
    )
    extraction_hints: Optional[str] = Field(
        None,
        max_length=1000,
        description="Hints for the AI on how to extract data",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Only allow lowercase alphanumeric and underscores
        import re

        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "Schema name must start with a lowercase letter and contain only lowercase letters, numbers, and underscores"
            )
        # Don't allow overwriting built-in schemas
        if v in EXTRACTION_SCHEMAS:
            raise ValueError(f"Cannot use built-in schema name: {v}")
        return v


class SchemaListItem(BaseModel):
    """Schema item for listing."""

    name: str
    description: str
    is_builtin: bool
    field_count: int


class SchemaListResponse(BaseModel):
    """Response for listing all schemas."""

    schemas: list[SchemaListItem]


class SchemaResponse(BaseModel):
    """Response for a single schema."""

    name: str
    description: str
    is_builtin: bool
    fields: list[SchemaField]
    extraction_hints: Optional[str] = None
    json_schema: dict[str, Any]


class SchemaCreateResponse(BaseModel):
    """Response for schema creation."""

    success: bool
    name: str
    message: str


class SchemaDeleteResponse(BaseModel):
    """Response for schema deletion."""

    success: bool
    name: str
    message: str


# =============================================================================
# Helper Functions
# =============================================================================


def _ensure_schemas_dir() -> None:
    """Ensure schemas directory exists."""
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)


def _get_custom_schema_path(name: str) -> Path:
    """Get path to a custom schema file."""
    return SCHEMAS_DIR / f"{name}.json"


def _load_custom_schema(name: str) -> Optional[dict[str, Any]]:
    """Load a custom schema from disk."""
    path = _get_custom_schema_path(name)
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Failed to load custom schema '%s': %s", name, e)
    return None


def _save_custom_schema(schema: SchemaDefinition) -> None:
    """Save a custom schema to disk."""
    _ensure_schemas_dir()
    path = _get_custom_schema_path(schema.name)
    with open(path, "w") as f:
        json.dump(schema.model_dump(), f, indent=2)


def _delete_custom_schema(name: str) -> bool:
    """Delete a custom schema from disk."""
    path = _get_custom_schema_path(name)
    if path.exists():
        path.unlink()
        return True
    return False


def _list_custom_schemas() -> list[str]:
    """List all custom schema names."""
    _ensure_schemas_dir()
    return [p.stem for p in SCHEMAS_DIR.glob("*.json")]


def _convert_to_json_schema(schema: SchemaDefinition) -> dict[str, Any]:
    """Convert a SchemaDefinition to a JSON Schema format for Claude extraction."""
    properties = {}
    required = []

    for field in schema.fields:
        field_schema: dict[str, Any] = {"type": field.type}

        if field.description:
            field_schema["description"] = field.description

        if field.type in ("integer", "number"):
            if field.min is not None:
                field_schema["minimum"] = field.min
            if field.max is not None:
                field_schema["maximum"] = field.max

        if field.type == "string" and field.enum:
            field_schema["enum"] = field.enum

        if field.type == "array":
            # Default to array of strings
            field_schema["items"] = {"type": "string"}

        properties[field.name] = field_schema

        if field.required:
            required.append(field.name)

    json_schema: dict[str, Any] = {
        "type": "object",
        "description": schema.description,
        "properties": properties,
    }

    if required:
        json_schema["required"] = required

    return json_schema


def _builtin_to_schema_response(name: str, schema: dict[str, Any]) -> SchemaResponse:
    """Convert a built-in schema to a SchemaResponse."""
    fields = []
    props = schema.get("properties", {})

    for field_name, field_def in props.items():
        # Handle nested schemas (like activities, tasks, meals)
        if field_def.get("type") == "array" and "items" in field_def:
            fields.append(
                SchemaField(
                    name=field_name,
                    type="array",
                    description=field_def.get("description", ""),
                    required=field_name in schema.get("required", []),
                )
            )
        else:
            fields.append(
                SchemaField(
                    name=field_name,
                    type=field_def.get("type", "string"),
                    description=field_def.get("description", ""),
                    required=field_name in schema.get("required", []),
                    min=field_def.get("minimum"),
                    max=field_def.get("maximum"),
                    enum=field_def.get("enum"),
                )
            )

    return SchemaResponse(
        name=name,
        description=schema.get("description", f"Built-in {name} schema"),
        is_builtin=True,
        fields=fields,
        extraction_hints=None,
        json_schema=schema,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("", response_model=SchemaListResponse)
def list_schemas() -> SchemaListResponse:
    """List all available extraction schemas.

    Returns both built-in schemas and custom user-defined schemas.

    Returns:
        List of schema summaries
    """
    schemas = []

    # Add built-in schemas
    for name, schema in EXTRACTION_SCHEMAS.items():
        field_count = len(schema.get("properties", {}))
        schemas.append(
            SchemaListItem(
                name=name,
                description=schema.get("description", f"Built-in {name} schema"),
                is_builtin=True,
                field_count=field_count,
            )
        )

    # Add custom schemas (skip files that don't match expected format)
    for name in _list_custom_schemas():
        custom_schema = _load_custom_schema(name)
        if custom_schema and "name" in custom_schema:
            schemas.append(
                SchemaListItem(
                    name=custom_schema["name"],
                    description=custom_schema.get("description", ""),
                    is_builtin=False,
                    field_count=len(custom_schema.get("fields", custom_schema.get("columns", []))),
                )
            )

    # Sort by name
    schemas.sort(key=lambda s: (not s.is_builtin, s.name))

    return SchemaListResponse(schemas=schemas)


@router.get("/{name}", response_model=SchemaResponse)
def get_schema(name: str) -> SchemaResponse:
    """Get a specific schema by name.

    Args:
        name: Schema name (built-in or custom)

    Returns:
        Full schema definition

    Raises:
        404: Schema not found
    """
    # Check built-in schemas first
    if name in EXTRACTION_SCHEMAS:
        return _builtin_to_schema_response(name, EXTRACTION_SCHEMAS[name])

    # Check custom schemas
    custom_schema = _load_custom_schema(name)
    if custom_schema:
        definition = SchemaDefinition(**custom_schema)
        return SchemaResponse(
            name=definition.name,
            description=definition.description,
            is_builtin=False,
            fields=definition.fields,
            extraction_hints=definition.extraction_hints,
            json_schema=_convert_to_json_schema(definition),
        )

    raise HTTPException(status_code=404, detail=f"Schema not found: {name}")


@router.post("", response_model=SchemaCreateResponse)
def create_schema(schema: SchemaDefinition) -> SchemaCreateResponse:
    """Create a new custom extraction schema.

    Args:
        schema: Schema definition

    Returns:
        Success response

    Raises:
        400: Invalid schema or name conflict
    """
    # Check if custom schema already exists
    if _load_custom_schema(schema.name):
        raise HTTPException(
            status_code=400, detail=f"Schema already exists: {schema.name}"
        )

    # Save the schema
    _save_custom_schema(schema)

    return SchemaCreateResponse(
        success=True,
        name=schema.name,
        message=f"Schema '{schema.name}' created successfully",
    )


@router.put("/{name}", response_model=SchemaCreateResponse)
def update_schema(name: str, schema: SchemaDefinition) -> SchemaCreateResponse:
    """Update an existing custom schema.

    Args:
        name: Schema name to update
        schema: Updated schema definition

    Returns:
        Success response

    Raises:
        400: Cannot update built-in schema
        404: Schema not found
    """
    # Cannot update built-in schemas
    if name in EXTRACTION_SCHEMAS:
        raise HTTPException(
            status_code=400, detail=f"Cannot update built-in schema: {name}"
        )

    # Check if schema exists
    if not _load_custom_schema(name):
        raise HTTPException(status_code=404, detail=f"Schema not found: {name}")

    # If name is changing, delete old file
    if schema.name != name:
        _delete_custom_schema(name)

    # Save updated schema
    _save_custom_schema(schema)

    return SchemaCreateResponse(
        success=True,
        name=schema.name,
        message=f"Schema '{schema.name}' updated successfully",
    )


@router.delete("/{name}", response_model=SchemaDeleteResponse)
def delete_schema(name: str) -> SchemaDeleteResponse:
    """Delete a custom schema.

    Args:
        name: Schema name to delete

    Returns:
        Success response

    Raises:
        400: Cannot delete built-in schema
        404: Schema not found
    """
    # Cannot delete built-in schemas
    if name in EXTRACTION_SCHEMAS:
        raise HTTPException(
            status_code=400, detail=f"Cannot delete built-in schema: {name}"
        )

    # Try to delete
    if _delete_custom_schema(name):
        return SchemaDeleteResponse(
            success=True,
            name=name,
            message=f"Schema '{name}' deleted successfully",
        )

    raise HTTPException(status_code=404, detail=f"Schema not found: {name}")


@router.get("/{name}/json-schema")
def get_json_schema(name: str) -> dict[str, Any]:
    """Get the JSON Schema format for a schema.

    This is the format used by Claude for extraction.

    Args:
        name: Schema name

    Returns:
        JSON Schema object

    Raises:
        404: Schema not found
    """
    # Check built-in schemas
    if name in EXTRACTION_SCHEMAS:
        return EXTRACTION_SCHEMAS[name]

    # Check custom schemas
    custom_schema = _load_custom_schema(name)
    if custom_schema:
        definition = SchemaDefinition(**custom_schema)
        return _convert_to_json_schema(definition)

    raise HTTPException(status_code=404, detail=f"Schema not found: {name}")
