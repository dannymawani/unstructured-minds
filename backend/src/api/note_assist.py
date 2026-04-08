"""Note-aware chat assistant API endpoint."""


from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..claude import ClaudeClient
from ..middleware import limiter
from ..middleware.rate_limit import RATE_LIMIT_CLAUDE_API
from ..middleware.validation import MAX_QUERY_LENGTH

router = APIRouter()


class ImageData(BaseModel):
    """Base64-encoded image."""

    data: str
    media_type: str


class NoteAssistRequest(BaseModel):
    """Request for note-aware chat assistance."""

    message: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    file_path: str | None = None
    file_content: str | None = Field(default=None, max_length=MAX_QUERY_LENGTH * 10)
    images: list[ImageData] | None = Field(default=None, max_length=5)


class NoteAssistResponse(BaseModel):
    """Response from note assistant."""

    reply: str
    updated_content: str | None = None


def get_claude(request: Request) -> ClaudeClient:
    """Get Claude client from app state."""
    return request.app.state.claude


@router.post("/chat/note-assist", response_model=NoteAssistResponse)
@limiter.limit(RATE_LIMIT_CLAUDE_API)
async def note_assist(
    request: Request,
    body: NoteAssistRequest,
    claude: ClaudeClient = Depends(get_claude),
) -> NoteAssistResponse:
    """Process a note-aware chat message with optional images.

    Args:
        request: HTTP request (required by slowapi rate limiter)
        body: Note assist request with message, file context, and optional images
        claude: Claude client for AI response

    Returns:
        Reply text and optionally updated note content
    """
    if not claude.is_configured:
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set LLM_API_KEY or ANTHROPIC_API_KEY.",
        )

    # Convert image models to dicts
    images = None
    if body.images:
        images = [{"data": img.data, "media_type": img.media_type} for img in body.images]

    try:
        result = await claude.note_assist(
            message=body.message,
            file_path=body.file_path,
            file_content=body.file_content,
            images=images,
        )

        return NoteAssistResponse(
            reply=result["reply"],
            updated_content=result.get("updated_content"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Note assist failed: {str(e)}")
