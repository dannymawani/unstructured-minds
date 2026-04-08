"""Webhooks API endpoints."""


from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from ..config import settings
from ..logging_config import get_logger
from ..webhooks import (
    WEBHOOK_EVENTS,
    Webhook,
    WebhookDispatcher,
    WebhookStorage,
)
from ..webhooks.models import (
    WebhookListResponse,
    WebhookResponse,
    WebhookTestResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_storage() -> WebhookStorage:
    """Get webhook storage instance."""
    return WebhookStorage(settings.data_path)


def get_dispatcher() -> WebhookDispatcher:
    """Get webhook dispatcher instance."""
    return WebhookDispatcher(get_storage())


def webhook_to_response(webhook: Webhook) -> WebhookResponse:
    """Convert a Webhook to WebhookResponse (without secret)."""
    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        name=webhook.name,
        active=webhook.active,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        last_triggered=webhook.last_triggered,
        failure_count=webhook.failure_count,
    )


class WebhookCreateRequest(BaseModel):
    """Request to create a webhook."""

    url: HttpUrl = Field(..., description="URL to receive webhook events")
    events: list[str] = Field(
        ...,
        min_length=1,
        description="List of events to subscribe to",
    )
    secret: str | None = Field(
        None,
        min_length=16,
        max_length=256,
        description="Secret key for signing payloads (recommended)",
    )
    name: str | None = Field(
        None,
        max_length=100,
        description="Human-readable name for the webhook",
    )


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook."""

    url: HttpUrl | None = Field(None, description="URL to receive webhook events")
    events: list[str] | None = Field(
        None,
        min_length=1,
        description="List of events to subscribe to",
    )
    secret: str | None = Field(
        None,
        min_length=16,
        max_length=256,
        description="Secret key for signing payloads",
    )
    name: str | None = Field(
        None,
        max_length=100,
        description="Human-readable name for the webhook",
    )
    active: bool | None = Field(None, description="Whether the webhook is active")


class WebhookEventsResponse(BaseModel):
    """Response listing available webhook events."""

    events: list[str]


@router.get("/events", response_model=WebhookEventsResponse)
async def list_webhook_events() -> WebhookEventsResponse:
    """List all available webhook events.

    Returns:
        List of event names that can be subscribed to
    """
    return WebhookEventsResponse(events=WEBHOOK_EVENTS)


@router.get("", response_model=WebhookListResponse)
async def list_webhooks() -> WebhookListResponse:
    """List all configured webhooks.

    Returns:
        List of webhooks (without secrets)
    """
    storage = get_storage()
    webhooks = storage.list_all()
    return WebhookListResponse(
        webhooks=[webhook_to_response(w) for w in webhooks],
        total=len(webhooks),
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(webhook_id: str) -> WebhookResponse:
    """Get a webhook by ID.

    Args:
        webhook_id: Webhook ID

    Returns:
        Webhook details (without secret)
    """
    storage = get_storage()
    webhook = storage.get(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found: {webhook_id}",
        )
    return webhook_to_response(webhook)


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(request: WebhookCreateRequest) -> WebhookResponse:
    """Create a new webhook.

    Args:
        request: Webhook configuration

    Returns:
        Created webhook (without secret)
    """
    # Validate events
    invalid_events = [e for e in request.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid events: {invalid_events}. Valid events: {WEBHOOK_EVENTS}",
        )

    storage = get_storage()

    # Check for duplicate URL
    existing = storage.list_all()
    for w in existing:
        if w.url == str(request.url):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Webhook already exists for URL: {request.url}",
            )

    webhook = Webhook(
        url=str(request.url),
        events=request.events,
        secret=request.secret,
        name=request.name,
    )
    created = storage.create(webhook)
    logger.info("webhook_created", webhook_id=created.id, url=created.url, events=created.events)
    return webhook_to_response(created)


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
) -> WebhookResponse:
    """Update a webhook.

    Args:
        webhook_id: Webhook ID
        request: Fields to update

    Returns:
        Updated webhook (without secret)
    """
    storage = get_storage()
    webhook = storage.get(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found: {webhook_id}",
        )

    # Validate events if provided
    if request.events:
        invalid_events = [e for e in request.events if e not in WEBHOOK_EVENTS]
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid events: {invalid_events}. Valid events: {WEBHOOK_EVENTS}",
            )
        webhook.events = request.events

    if request.url is not None:
        webhook.url = str(request.url)
    if request.secret is not None:
        webhook.secret = request.secret
    if request.name is not None:
        webhook.name = request.name
    if request.active is not None:
        webhook.active = request.active

    updated = storage.update(webhook)
    logger.info("webhook_updated", webhook_id=updated.id)
    return webhook_to_response(updated)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(webhook_id: str) -> None:
    """Delete a webhook.

    Args:
        webhook_id: Webhook ID
    """
    storage = get_storage()
    if not storage.delete(webhook_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found: {webhook_id}",
        )
    logger.info("webhook_deleted", webhook_id=webhook_id)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(webhook_id: str) -> WebhookTestResponse:
    """Send a test event to a webhook.

    Args:
        webhook_id: Webhook ID

    Returns:
        Test result with status code and timing
    """
    storage = get_storage()
    webhook = storage.get(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found: {webhook_id}",
        )

    dispatcher = get_dispatcher()
    result = await dispatcher.test(webhook)

    logger.info(
        "webhook_tested",
        webhook_id=webhook_id,
        success=result.success,
        status_code=result.status_code,
        duration_ms=round(result.duration_ms, 2),
    )

    return WebhookTestResponse(
        success=result.success,
        status_code=result.status_code,
        error=result.error,
        duration_ms=result.duration_ms,
    )


@router.post("/{webhook_id}/toggle", response_model=WebhookResponse)
async def toggle_webhook(webhook_id: str) -> WebhookResponse:
    """Toggle a webhook's active status.

    Args:
        webhook_id: Webhook ID

    Returns:
        Updated webhook
    """
    storage = get_storage()
    webhook = storage.get(webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found: {webhook_id}",
        )

    webhook.active = not webhook.active
    updated = storage.update(webhook)
    logger.info("webhook_toggled", webhook_id=updated.id, active=updated.active)
    return webhook_to_response(updated)
