"""Webhook storage using JSON file."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..logging_config import get_logger
from .models import Webhook

logger = get_logger(__name__)


class WebhookStorage:
    """JSON file-based storage for webhook configurations."""

    def __init__(self, data_path: Path) -> None:
        """Initialize webhook storage.

        Args:
            data_path: Path to the data directory
        """
        self._file_path = data_path / "webhooks.json"
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the webhooks file exists."""
        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_webhooks([])

    def _load_webhooks(self) -> list[dict]:
        """Load webhooks from JSON file."""
        try:
            with open(self._file_path, "r") as f:
                data = json.load(f)
                return data.get("webhooks", [])
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("webhook_storage_load_error", error=str(e))
            return []

    def _save_webhooks(self, webhooks: list[dict]) -> None:
        """Save webhooks to JSON file."""
        with open(self._file_path, "w") as f:
            json.dump(
                {
                    "webhooks": webhooks,
                    "updated_at": datetime.utcnow().isoformat(),
                },
                f,
                indent=2,
                default=str,
            )

    def list_all(self) -> list[Webhook]:
        """List all webhooks.

        Returns:
            List of webhook configurations
        """
        data = self._load_webhooks()
        webhooks = []
        for item in data:
            try:
                webhooks.append(Webhook(**item))
            except Exception as e:
                logger.warning("webhook_parse_error", webhook_id=item.get("id"), error=str(e))
        return webhooks

    def get(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID.

        Args:
            webhook_id: Webhook ID

        Returns:
            Webhook if found, None otherwise
        """
        webhooks = self.list_all()
        for webhook in webhooks:
            if webhook.id == webhook_id:
                return webhook
        return None

    def create(self, webhook: Webhook) -> Webhook:
        """Create a new webhook.

        Args:
            webhook: Webhook to create

        Returns:
            Created webhook
        """
        webhooks = self._load_webhooks()
        webhooks.append(webhook.model_dump(mode="json"))
        self._save_webhooks(webhooks)
        logger.info("webhook_created", webhook_id=webhook.id, url=webhook.url)
        return webhook

    def update(self, webhook: Webhook) -> Webhook:
        """Update an existing webhook.

        Args:
            webhook: Webhook to update

        Returns:
            Updated webhook
        """
        webhooks = self._load_webhooks()
        for i, item in enumerate(webhooks):
            if item.get("id") == webhook.id:
                webhook.updated_at = datetime.utcnow()
                webhooks[i] = webhook.model_dump(mode="json")
                self._save_webhooks(webhooks)
                logger.info("webhook_updated", webhook_id=webhook.id)
                return webhook
        raise ValueError(f"Webhook not found: {webhook.id}")

    def delete(self, webhook_id: str) -> bool:
        """Delete a webhook.

        Args:
            webhook_id: Webhook ID to delete

        Returns:
            True if deleted, False if not found
        """
        webhooks = self._load_webhooks()
        original_count = len(webhooks)
        webhooks = [w for w in webhooks if w.get("id") != webhook_id]
        if len(webhooks) < original_count:
            self._save_webhooks(webhooks)
            logger.info("webhook_deleted", webhook_id=webhook_id)
            return True
        return False

    def get_by_event(self, event: str) -> list[Webhook]:
        """Get webhooks subscribed to a specific event.

        Args:
            event: Event name

        Returns:
            List of webhooks subscribed to the event
        """
        webhooks = self.list_all()
        return [w for w in webhooks if event in w.events and w.active]

    def record_success(self, webhook_id: str) -> None:
        """Record a successful webhook delivery.

        Args:
            webhook_id: Webhook ID
        """
        webhook = self.get(webhook_id)
        if webhook:
            webhook.last_triggered = datetime.utcnow()
            webhook.failure_count = 0
            self.update(webhook)

    def record_failure(self, webhook_id: str) -> None:
        """Record a failed webhook delivery.

        Args:
            webhook_id: Webhook ID
        """
        webhook = self.get(webhook_id)
        if webhook:
            webhook.last_triggered = datetime.utcnow()
            webhook.failure_count += 1
            self.update(webhook)
