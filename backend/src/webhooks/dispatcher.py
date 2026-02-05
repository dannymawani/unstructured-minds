"""Webhook event dispatcher."""

import asyncio
import hashlib
import hmac
import time
from datetime import datetime
from typing import Any, Optional

import httpx

from ..config import settings
from ..logging_config import get_logger
from .models import (
    Webhook,
    WebhookDeliveryResult,
    WebhookEvent,
    WebhookPayload,
)
from .storage import WebhookStorage

logger = get_logger(__name__)

# Timeout for webhook requests
WEBHOOK_TIMEOUT = 10.0  # seconds

# Maximum retries for failed webhooks
MAX_RETRIES = 3

# Retry delay in seconds
RETRY_DELAY = 1.0


def compute_signature(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a payload.

    Args:
        payload: JSON payload string
        secret: Secret key

    Returns:
        Signature string prefixed with sha256=
    """
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify a webhook signature.

    Args:
        payload: JSON payload string
        signature: Signature to verify
        secret: Secret key

    Returns:
        True if signature is valid
    """
    expected = compute_signature(payload, secret)
    return hmac.compare_digest(signature, expected)


class WebhookDispatcher:
    """Dispatches webhook events to configured endpoints."""

    def __init__(self, storage: WebhookStorage) -> None:
        """Initialize the dispatcher.

        Args:
            storage: Webhook storage backend
        """
        self._storage = storage
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _create_payload(
        self, event: str, data: dict[str, Any], webhook_id: str, secret: Optional[str] = None
    ) -> tuple[WebhookPayload, str]:
        """Create a webhook payload.

        Args:
            event: Event name
            data: Event data
            webhook_id: Webhook ID
            secret: Optional secret for signing

        Returns:
            Tuple of (WebhookPayload, JSON string)
        """
        payload = WebhookPayload(
            event=event,
            timestamp=datetime.utcnow().isoformat() + "Z",
            webhook_id=webhook_id,
            data=data,
        )

        # Convert to JSON string
        payload_json = payload.model_dump_json()

        # Add signature if secret provided
        if secret:
            payload.signature = compute_signature(payload_json, secret)
            # Re-serialize with signature
            payload_json = payload.model_dump_json()

        return payload, payload_json

    async def _deliver(
        self, webhook: Webhook, event: str, data: dict[str, Any]
    ) -> WebhookDeliveryResult:
        """Deliver an event to a webhook endpoint.

        Args:
            webhook: Webhook configuration
            event: Event name
            data: Event data

        Returns:
            Delivery result
        """
        start_time = time.perf_counter()
        client = await self._get_client()

        try:
            payload, payload_json = self._create_payload(
                event, data, webhook.id, webhook.secret
            )

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "UnstructuredMinds-Webhook/1.0",
                "X-Webhook-Event": event,
                "X-Webhook-ID": webhook.id,
            }

            if payload.signature:
                headers["X-Webhook-Signature"] = payload.signature

            response = await client.post(
                webhook.url,
                content=payload_json,
                headers=headers,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000
            success = 200 <= response.status_code < 300

            if success:
                self._storage.record_success(webhook.id)
                logger.info(
                    "webhook_delivered",
                    webhook_id=webhook.id,
                    event=event,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )
            else:
                self._storage.record_failure(webhook.id)
                logger.warning(
                    "webhook_delivery_failed",
                    webhook_id=webhook.id,
                    event=event,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

            return WebhookDeliveryResult(
                webhook_id=webhook.id,
                event=event,
                success=success,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        except httpx.TimeoutException:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._storage.record_failure(webhook.id)
            logger.warning(
                "webhook_timeout",
                webhook_id=webhook.id,
                event=event,
                duration_ms=round(duration_ms, 2),
            )
            return WebhookDeliveryResult(
                webhook_id=webhook.id,
                event=event,
                success=False,
                error="Request timed out",
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._storage.record_failure(webhook.id)
            logger.error(
                "webhook_error",
                webhook_id=webhook.id,
                event=event,
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            return WebhookDeliveryResult(
                webhook_id=webhook.id,
                event=event,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def dispatch(
        self, event: str, data: dict[str, Any]
    ) -> list[WebhookDeliveryResult]:
        """Dispatch an event to all subscribed webhooks.

        Args:
            event: Event name
            data: Event data

        Returns:
            List of delivery results
        """
        webhooks = self._storage.get_by_event(event)

        if not webhooks:
            logger.debug("webhook_no_subscribers", event=event)
            return []

        logger.info("webhook_dispatching", event=event, webhook_count=len(webhooks))

        # Dispatch to all webhooks concurrently
        tasks = [self._deliver(webhook, event, data) for webhook in webhooks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to results
        delivery_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                delivery_results.append(
                    WebhookDeliveryResult(
                        webhook_id=webhooks[i].id,
                        event=event,
                        success=False,
                        error=str(result),
                        duration_ms=0,
                    )
                )
            else:
                delivery_results.append(result)

        return delivery_results

    async def test(self, webhook: Webhook) -> WebhookDeliveryResult:
        """Send a test event to a webhook.

        Args:
            webhook: Webhook to test

        Returns:
            Delivery result
        """
        test_data = {
            "message": "This is a test webhook delivery",
            "test": True,
        }
        return await self._deliver(webhook, "test", test_data)


# Global dispatcher instance (initialized lazily)
_dispatcher: Optional[WebhookDispatcher] = None


def get_dispatcher() -> WebhookDispatcher:
    """Get or create the global webhook dispatcher.

    Returns:
        Webhook dispatcher instance
    """
    global _dispatcher
    if _dispatcher is None:
        storage = WebhookStorage(settings.data_path)
        _dispatcher = WebhookDispatcher(storage)
    return _dispatcher


async def dispatch_event(event: str, data: dict[str, Any]) -> list[WebhookDeliveryResult]:
    """Dispatch a webhook event.

    This is a convenience function that uses the global dispatcher.

    Args:
        event: Event name (use WebhookEvent enum values)
        data: Event data

    Returns:
        List of delivery results
    """
    dispatcher = get_dispatcher()
    return await dispatcher.dispatch(event, data)
