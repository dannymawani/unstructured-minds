"""Chat API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..claude import ClaudeClient
from ..db import DatabaseManager


router = APIRouter()


class ChatMessage(BaseModel):
    """A chat message."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request for chat completion."""

    message: str
    context: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from chat completion."""

    message: ChatMessage
    context_used: bool


def get_db(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db


def get_claude(request: Request) -> ClaudeClient:
    """Get Claude client from app state."""
    return request.app.state.claude


async def gather_context(db: DatabaseManager, query: str) -> str:
    """Gather relevant context from database for the query.

    Args:
        db: Database manager
        query: User's query

    Returns:
        Formatted context string
    """
    context_parts = []

    # Get recent exercise logs
    try:
        result = db.execute(
            """
            SELECT date, exercise_type, duration_minutes, notes
            FROM exercise_log
            ORDER BY date DESC
            LIMIT 10
            """
        )
        if result:
            context_parts.append("Recent exercise logs:")
            for row in result:
                context_parts.append(
                    f"  - {row[0]}: {row[1]} for {row[2]} minutes ({row[3] or 'no notes'})"
                )
    except Exception:
        pass  # Table may not exist yet

    # Get recent daily metrics
    try:
        result = db.execute(
            """
            SELECT date, metric_name, value, unit
            FROM daily_metrics
            ORDER BY date DESC
            LIMIT 10
            """
        )
        if result:
            context_parts.append("\nRecent daily metrics:")
            for row in result:
                context_parts.append(f"  - {row[0]}: {row[1]} = {row[2]} {row[3] or ''}")
    except Exception:
        pass  # Table may not exist yet

    # Get recent activities
    try:
        result = db.execute(
            """
            SELECT date, category, activity, notes
            FROM activities
            ORDER BY date DESC
            LIMIT 10
            """
        )
        if result:
            context_parts.append("\nRecent activities:")
            for row in result:
                context_parts.append(f"  - {row[0]}: [{row[1]}] {row[2]} ({row[3] or 'no notes'})")
    except Exception:
        pass  # Table may not exist yet

    return "\n".join(context_parts) if context_parts else "No data available yet."


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: DatabaseManager = Depends(get_db),
    claude: ClaudeClient = Depends(get_claude),
) -> ChatResponse:
    """Process a chat message and return a response.

    Args:
        request: Chat request with user message
        db: Database manager for context
        claude: Claude client for AI response

    Returns:
        Chat response with assistant message
    """
    if not claude.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Claude API not configured. Set ANTHROPIC_API_KEY environment variable.",
        )

    # Gather context from database
    context = request.context or await gather_context(db, request.message)
    context_used = bool(context and context != "No data available yet.")

    try:
        response_text = await claude.query(request.message, context)

        return ChatResponse(
            message=ChatMessage(role="assistant", content=response_text),
            context_used=context_used,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
