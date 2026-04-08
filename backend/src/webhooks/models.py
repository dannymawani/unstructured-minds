"""Webhook data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class WebhookEvent(str, Enum):
    """Supported webhook events."""

    NOTE_CREATED = "note.created"
    NOTE_UPDATED = "note.updated"
    NOTE_DELETED = "note.deleted"
    EXTRACTION_COMPLETED = "extraction.completed"
    DAILY_CREATED = "daily.created"


# All available events for validation
WEBHOOK_EVENTS = [e.value for e in WebhookEvent]


class WebhookCreate(BaseModel):
    """Request model for creating a webhook."""

    url: HttpUrl = Field(..., description="URL to receive webhook events")
    events: list[str] = Field(
        ...,
        min_length=1,
        description="List of events to subscribe to",
    )
    secret: Optional[str] = Field(
        None,
        min_length=16,
        max_length=256,
        description="Secret key for signing payloads (optional)",
    )
    name: Optional[str] = Field(
        None,
        max_length=100,
        description="Human-readable name for the webhook",
    )
    active: bool = Field(True, description="Whether the webhook is active")


class Webhook(BaseModel):
    """Webhook configuration."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str
    events: list[str]
    secret: Optional[str] = None
    name: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    failure_count: int = 0

    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Payload sent to webhook endpoints."""

    event: str
    timestamp: str
    webhook_id: str
    data: dict[str, Any]
    signature: Optional[str] = None


class WebhookDeliveryResult(BaseModel):
    """Result of a webhook delivery attempt."""

    webhook_id: str
    event: str
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    duration_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebhookResponse(BaseModel):
    """Response model for webhook operations."""

    id: str
    url: str
    events: list[str]
    name: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime
    last_triggered: Optional[datetime]
    failure_count: int


class WebhookListResponse(BaseModel):
    """Response model for listing webhooks."""

    webhooks: list[WebhookResponse]
    total: int


class WebhookTestResponse(BaseModel):
    """Response model for testing a webhook."""

    success: bool
    status_code: Optional[int]
    error: Optional[str]
    duration_ms: float
