"""Templates API endpoints."""

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..storage import StorageBackend
from .dependencies import get_storage as _dep_get_storage

router = APIRouter()


TEMPLATES_FOLDER = "Templates"


class TemplateInfo(BaseModel):
    """Information about a template."""

    name: str
    description: str


class TemplateListResponse(BaseModel):
    """Response listing available templates."""

    templates: list[TemplateInfo]


class TemplateContentResponse(BaseModel):
    """Response with template content."""

    name: str
    content: str


class CreateFromTemplateRequest(BaseModel):
    """Request to create a note from a template."""

    template_name: str
    title: str
    folder: str | None = None  # Optional folder path for the new note


class CreateFromTemplateResponse(BaseModel):
    """Response from creating a note from template."""

    success: bool
    path: str
    message: str


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend (user-scoped in cloud mode)."""
    return _dep_get_storage(request)


def substitute_variables(content: str, title: str) -> str:
    """Substitute template variables in content.

    Supported variables:
    - {{date}} -> YYYY-MM-DD
    - {{date:FORMAT}} -> Custom format (e.g., {{date:YYYY}} -> 2026)
    - {{time}} -> HH:MM
    - {{time:FORMAT}} -> Custom format (e.g., {{time:HH:MM:SS}})
    - {{title}} -> Note title
    - {{datetime}} -> Full ISO datetime

    Args:
        content: Template content with variables
        title: Note title to substitute

    Returns:
        Content with variables replaced
    """
    now = datetime.now()

    # Replace {{title}}
    content = content.replace("{{title}}", title)

    # Replace {{datetime}}
    content = content.replace("{{datetime}}", now.isoformat())

    # Replace {{date}} and {{date:FORMAT}}
    def replace_date(match: re.Match) -> str:
        format_str = match.group(1)
        if format_str:
            # Convert common format tokens to strftime
            fmt = format_str
            fmt = fmt.replace("YYYY", "%Y")
            fmt = fmt.replace("YY", "%y")
            fmt = fmt.replace("MM", "%m")
            fmt = fmt.replace("DD", "%d")
            fmt = fmt.replace("MMMM", "%B")
            fmt = fmt.replace("MMM", "%b")
            fmt = fmt.replace("dddd", "%A")
            fmt = fmt.replace("ddd", "%a")
            return now.strftime(fmt)
        return now.strftime("%Y-%m-%d")

    content = re.sub(r"\{\{date(?::([^}]+))?\}\}", replace_date, content)

    # Replace {{time}} and {{time:FORMAT}}
    def replace_time(match: re.Match) -> str:
        format_str = match.group(1)
        if format_str:
            fmt = format_str
            fmt = fmt.replace("HH", "%H")
            fmt = fmt.replace("hh", "%I")
            fmt = fmt.replace("mm", "%M")
            fmt = fmt.replace("MM", "%M")
            fmt = fmt.replace("ss", "%S")
            fmt = fmt.replace("SS", "%S")
            fmt = fmt.replace("A", "%p")
            fmt = fmt.replace("a", "%p")
            return now.strftime(fmt)
        return now.strftime("%H:%M")

    content = re.sub(r"\{\{time(?::([^}]+))?\}\}", replace_time, content)

    return content


def extract_template_description(content: str) -> str:
    """Extract description from template frontmatter or first heading.

    Args:
        content: Template content

    Returns:
        Description string
    """
    # Try to find description in frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if frontmatter_match:
        frontmatter = frontmatter_match.group(1)
        desc_match = re.search(r"description:\s*(.+)", frontmatter)
        if desc_match:
            return desc_match.group(1).strip().strip('"\'')

    # Try to find first heading
    heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()

    return "Template"


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    storage: StorageBackend = Depends(get_storage),
) -> TemplateListResponse:
    """List all available templates.

    Templates are stored in the vault/Templates/ folder.
    Each .md file is considered a template.

    Returns:
        List of template names and descriptions
    """
    templates = []

    try:
        files = await storage.list(TEMPLATES_FOLDER)
        for file_path in files:
            if file_path.endswith(".md"):
                name = file_path.split("/")[-1].replace(".md", "")
                try:
                    content_bytes = await storage.read(file_path)
                    content = content_bytes.decode("utf-8")
                    description = extract_template_description(content)
                except Exception:
                    description = "Template"

                templates.append(TemplateInfo(name=name, description=description))
    except FileNotFoundError:
        # Templates folder doesn't exist yet, return empty list
        pass

    return TemplateListResponse(templates=templates)


@router.get("/templates/{name}", response_model=TemplateContentResponse)
async def get_template(
    name: str,
    storage: StorageBackend = Depends(get_storage),
) -> TemplateContentResponse:
    """Get template content by name.

    Args:
        name: Template name (without .md extension)

    Returns:
        Template content

    Raises:
        404: Template not found
    """
    file_path = f"{TEMPLATES_FOLDER}/{name}.md"

    try:
        content_bytes = await storage.read(file_path)
        content = content_bytes.decode("utf-8")
        return TemplateContentResponse(name=name, content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")


@router.post("/notes/from-template", response_model=CreateFromTemplateResponse)
async def create_from_template(
    request: CreateFromTemplateRequest,
    storage: StorageBackend = Depends(get_storage),
) -> CreateFromTemplateResponse:
    """Create a new note from a template.

    Substitutes template variables:
    - {{date}} -> Current date (YYYY-MM-DD)
    - {{date:FORMAT}} -> Custom date format
    - {{time}} -> Current time (HH:MM)
    - {{time:FORMAT}} -> Custom time format
    - {{title}} -> Note title
    - {{datetime}} -> Full ISO datetime

    Args:
        request: Template name, title, and optional folder

    Returns:
        Path to created note

    Raises:
        404: Template not found
        400: Note already exists
    """
    template_path = f"{TEMPLATES_FOLDER}/{request.template_name}.md"

    # Read template
    try:
        template_bytes = await storage.read(template_path)
        template_content = template_bytes.decode("utf-8")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Template not found: {request.template_name}"
        )

    # Substitute variables
    content = substitute_variables(template_content, request.title)

    # Determine output path
    safe_title = re.sub(r'[<>:"/\\|?*]', "-", request.title)  # Remove invalid chars
    if request.folder:
        folder = request.folder.strip("/")
        note_path = f"{folder}/{safe_title}.md"
    else:
        note_path = f"{safe_title}.md"

    # Check if file already exists
    if await storage.exists(note_path):
        raise HTTPException(
            status_code=400, detail=f"Note already exists: {note_path}"
        )

    # Write the new note
    await storage.write(note_path, content.encode("utf-8"))

    return CreateFromTemplateResponse(
        success=True,
        path=note_path,
        message=f"Created note from template '{request.template_name}'",
    )
