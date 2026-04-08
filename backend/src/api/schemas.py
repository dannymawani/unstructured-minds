"""Schema management API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from ..extraction.schemas import EXTRACTION_SCHEMAS
from ..storage.datastore import DataStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schemas", tags=["schemas"])


SCHEMAS_PREFIX = "schemas"


def _get_datastore(request: Request) -> DataStore:
    return request.app.state.datastore


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
    description: str | None = Field(
        None, max_length=500, description="Field description"
    )
    min: float | None = Field(None, description="Minimum value (for numbers)")
    max: float | None = Field(None, description="Maximum value (for numbers)")
    enum: list[str] | None = Field(
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
    extraction_hints: str | None = Field(
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
    extraction_hints: str | None = None
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


def _schema_path(name: str) -> str:
    """Get the datastore path for a custom schema."""
    return f"{SCHEMAS_PREFIX}/{name}.json"


async def _load_custom_schema(datastore: DataStore, name: str) -> dict[str, Any] | None:
    """Load a custom schema from the datastore."""
    data = await datastore.read_json(_schema_path(name))
    if data and "name" in data:
        return data
    return None


async def _save_custom_schema(datastore: DataStore, schema: SchemaDefinition) -> None:
    """Save a custom schema to the datastore."""
    await datastore.write_json(_schema_path(schema.name), schema.model_dump())


async def _delete_custom_schema(datastore: DataStore, name: str) -> bool:
    """Delete a custom schema from the datastore."""
    return await datastore.delete_file(_schema_path(name))


async def _list_custom_schemas(datastore: DataStore) -> list[str]:
    """List all custom schema names."""
    files = await datastore.list_files(SCHEMAS_PREFIX)
    names = []
    for f in files:
        # f is like "schemas/foo.json" — extract the stem
        if f.endswith(".json"):
            stem = f.rsplit("/", 1)[-1].removesuffix(".json")
            names.append(stem)
    return names


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
async def list_schemas(request: Request) -> SchemaListResponse:
    """List all available extraction schemas."""
    datastore = _get_datastore(request)
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

    # Add custom schemas
    for name in await _list_custom_schemas(datastore):
        custom_schema = await _load_custom_schema(datastore, name)
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
async def get_schema(name: str, request: Request) -> SchemaResponse:
    """Get a specific schema by name."""
    # Check built-in schemas first
    if name in EXTRACTION_SCHEMAS:
        return _builtin_to_schema_response(name, EXTRACTION_SCHEMAS[name])

    # Check custom schemas
    datastore = _get_datastore(request)
    custom_schema = await _load_custom_schema(datastore, name)
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
async def create_schema(schema: SchemaDefinition, request: Request) -> SchemaCreateResponse:
    """Create a new custom extraction schema."""
    datastore = _get_datastore(request)

    if await _load_custom_schema(datastore, schema.name):
        raise HTTPException(
            status_code=400, detail=f"Schema already exists: {schema.name}"
        )

    await _save_custom_schema(datastore, schema)

    return SchemaCreateResponse(
        success=True,
        name=schema.name,
        message=f"Schema '{schema.name}' created successfully",
    )


@router.put("/{name}", response_model=SchemaCreateResponse)
async def update_schema(name: str, schema: SchemaDefinition, request: Request) -> SchemaCreateResponse:
    """Update an existing custom schema."""
    datastore = _get_datastore(request)

    if name in EXTRACTION_SCHEMAS:
        raise HTTPException(
            status_code=400, detail=f"Cannot update built-in schema: {name}"
        )

    if not await _load_custom_schema(datastore, name):
        raise HTTPException(status_code=404, detail=f"Schema not found: {name}")

    # If name is changing, delete old file
    if schema.name != name:
        await _delete_custom_schema(datastore, name)

    await _save_custom_schema(datastore, schema)

    return SchemaCreateResponse(
        success=True,
        name=schema.name,
        message=f"Schema '{schema.name}' updated successfully",
    )


@router.delete("/{name}", response_model=SchemaDeleteResponse)
async def delete_schema(name: str, request: Request) -> SchemaDeleteResponse:
    """Delete a custom schema."""
    datastore = _get_datastore(request)

    if name in EXTRACTION_SCHEMAS:
        raise HTTPException(
            status_code=400, detail=f"Cannot delete built-in schema: {name}"
        )

    if await _delete_custom_schema(datastore, name):
        return SchemaDeleteResponse(
            success=True,
            name=name,
            message=f"Schema '{name}' deleted successfully",
        )

    raise HTTPException(status_code=404, detail=f"Schema not found: {name}")


@router.get("/{name}/json-schema")
async def get_json_schema(name: str, request: Request) -> dict[str, Any]:
    """Get the JSON Schema format for a schema."""
    if name in EXTRACTION_SCHEMAS:
        return EXTRACTION_SCHEMAS[name]

    datastore = _get_datastore(request)
    custom_schema = await _load_custom_schema(datastore, name)
    if custom_schema:
        definition = SchemaDefinition(**custom_schema)
        return _convert_to_json_schema(definition)

    raise HTTPException(status_code=404, detail=f"Schema not found: {name}")
