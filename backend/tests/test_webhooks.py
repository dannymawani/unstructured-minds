"""Tests for webhooks functionality."""

import json
from pathlib import Path

import pytest


class TestWebhookModels:
    """Tests for webhook data models."""

    def test_webhook_event_enum(self):
        """Test webhook event enum values."""
        from src.webhooks.models import WebhookEvent

        assert WebhookEvent.NOTE_CREATED.value == "note.created"
        assert WebhookEvent.NOTE_UPDATED.value == "note.updated"
        assert WebhookEvent.NOTE_DELETED.value == "note.deleted"
        assert WebhookEvent.EXTRACTION_COMPLETED.value == "extraction.completed"
        assert WebhookEvent.DAILY_CREATED.value == "daily.created"

    def test_webhook_events_list(self):
        """Test webhook events list."""
        from src.webhooks.models import WEBHOOK_EVENTS

        assert "note.created" in WEBHOOK_EVENTS
        assert "note.updated" in WEBHOOK_EVENTS
        assert "note.deleted" in WEBHOOK_EVENTS
        assert "extraction.completed" in WEBHOOK_EVENTS
        assert "daily.created" in WEBHOOK_EVENTS
        assert len(WEBHOOK_EVENTS) == 5

    def test_webhook_model(self):
        """Test Webhook model creation."""
        from src.webhooks.models import Webhook

        webhook = Webhook(
            url="https://example.com/webhook",
            events=["note.created", "note.updated"],
            name="Test Webhook",
            secret="my-secret-key-12345",
        )

        assert webhook.url == "https://example.com/webhook"
        assert webhook.events == ["note.created", "note.updated"]
        assert webhook.name == "Test Webhook"
        assert webhook.secret == "my-secret-key-12345"
        assert webhook.active is True
        assert webhook.failure_count == 0
        assert webhook.id is not None

    def test_webhook_payload_model(self):
        """Test WebhookPayload model creation."""
        from src.webhooks.models import WebhookPayload

        payload = WebhookPayload(
            event="note.created",
            timestamp="2026-02-05T14:30:00Z",
            webhook_id="test-id",
            data={"path": "test.md"},
        )

        assert payload.event == "note.created"
        assert payload.timestamp == "2026-02-05T14:30:00Z"
        assert payload.webhook_id == "test-id"
        assert payload.data == {"path": "test.md"}
        assert payload.signature is None


class TestWebhookStorage:
    """Tests for webhook storage."""

    def test_create_and_list(self, tmp_path: Path):
        """Test creating and listing webhooks."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        # Initially empty
        assert storage.list_all() == []

        # Create a webhook
        webhook = Webhook(
            url="https://example.com/test",
            events=["note.created"],
            name="Test",
        )
        created = storage.create(webhook)

        assert created.id == webhook.id
        assert created.url == "https://example.com/test"

        # List should have one
        webhooks = storage.list_all()
        assert len(webhooks) == 1
        assert webhooks[0].id == webhook.id

    def test_storage_persistence(self, tmp_path: Path):
        """Test that webhooks persist to file."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        # Create a webhook
        webhook = Webhook(
            url="https://example.com/persist",
            events=["note.created"],
            name="Persistent",
        )
        storage.create(webhook)

        # Verify file exists
        webhooks_file = tmp_path / "webhooks.json"
        assert webhooks_file.exists()

        # Read file content directly
        with open(webhooks_file) as f:
            data = json.load(f)

        assert len(data["webhooks"]) == 1
        assert data["webhooks"][0]["url"] == "https://example.com/persist"

        # Create new storage instance and verify data loads
        storage2 = WebhookStorage(tmp_path)
        webhooks = storage2.list_all()
        assert len(webhooks) == 1
        assert webhooks[0].url == "https://example.com/persist"

    def test_get_webhook(self, tmp_path: Path):
        """Test getting a specific webhook."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        webhook = Webhook(
            url="https://example.com/get",
            events=["note.created"],
        )
        storage.create(webhook)

        # Get by ID
        found = storage.get(webhook.id)
        assert found is not None
        assert found.url == "https://example.com/get"

        # Get non-existent
        not_found = storage.get("non-existent-id")
        assert not_found is None

    def test_update_webhook(self, tmp_path: Path):
        """Test updating a webhook."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        webhook = Webhook(
            url="https://example.com/update",
            events=["note.created"],
            name="Original",
        )
        storage.create(webhook)

        # Update
        webhook.name = "Updated"
        webhook.events = ["note.created", "note.updated"]
        updated = storage.update(webhook)

        assert updated.name == "Updated"
        assert "note.updated" in updated.events

        # Verify persisted
        found = storage.get(webhook.id)
        assert found.name == "Updated"

    def test_delete_webhook(self, tmp_path: Path):
        """Test deleting a webhook."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        webhook = Webhook(
            url="https://example.com/delete",
            events=["note.created"],
        )
        storage.create(webhook)

        # Delete
        result = storage.delete(webhook.id)
        assert result is True

        # Verify deleted
        assert storage.get(webhook.id) is None
        assert len(storage.list_all()) == 0

        # Delete non-existent
        result = storage.delete("non-existent-id")
        assert result is False

    def test_get_by_event(self, tmp_path: Path):
        """Test getting webhooks by event."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        # Create webhooks with different events
        webhook1 = Webhook(
            url="https://example.com/1",
            events=["note.created", "note.updated"],
        )
        webhook2 = Webhook(
            url="https://example.com/2",
            events=["note.deleted"],
        )
        webhook3 = Webhook(
            url="https://example.com/3",
            events=["note.created"],
            active=False,  # Inactive
        )
        storage.create(webhook1)
        storage.create(webhook2)
        storage.create(webhook3)

        # Get by note.created - should get webhook1 only (webhook3 is inactive)
        note_created = storage.get_by_event("note.created")
        assert len(note_created) == 1
        assert note_created[0].url == "https://example.com/1"

        # Get by note.deleted
        note_deleted = storage.get_by_event("note.deleted")
        assert len(note_deleted) == 1
        assert note_deleted[0].url == "https://example.com/2"

        # Get by non-existent event
        no_webhooks = storage.get_by_event("extraction.completed")
        assert len(no_webhooks) == 0

    def test_record_success(self, tmp_path: Path):
        """Test recording successful delivery."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        webhook = Webhook(
            url="https://example.com/success",
            events=["note.created"],
        )
        webhook.failure_count = 3  # Set some failures
        storage.create(webhook)

        # Record success
        storage.record_success(webhook.id)

        # Verify failure count reset
        found = storage.get(webhook.id)
        assert found.failure_count == 0
        assert found.last_triggered is not None

    def test_record_failure(self, tmp_path: Path):
        """Test recording failed delivery."""
        from src.webhooks.storage import WebhookStorage
        from src.webhooks.models import Webhook

        storage = WebhookStorage(tmp_path)

        webhook = Webhook(
            url="https://example.com/failure",
            events=["note.created"],
        )
        storage.create(webhook)

        # Record failures
        storage.record_failure(webhook.id)
        storage.record_failure(webhook.id)

        # Verify failure count incremented
        found = storage.get(webhook.id)
        assert found.failure_count == 2
        assert found.last_triggered is not None


class TestWebhookSignature:
    """Tests for webhook signature computation."""

    def test_compute_signature(self):
        """Test signature computation."""
        from src.webhooks.dispatcher import compute_signature

        payload = '{"event": "test"}'
        secret = "my-secret-key"

        signature = compute_signature(payload, secret)

        assert signature.startswith("sha256=")
        assert len(signature) == 7 + 64  # "sha256=" + 64 hex chars

    def test_signature_is_deterministic(self):
        """Test that same input produces same signature."""
        from src.webhooks.dispatcher import compute_signature

        payload = '{"event": "test"}'
        secret = "my-secret-key"

        sig1 = compute_signature(payload, secret)
        sig2 = compute_signature(payload, secret)

        assert sig1 == sig2

    def test_different_payload_different_signature(self):
        """Test that different payloads produce different signatures."""
        from src.webhooks.dispatcher import compute_signature

        secret = "my-secret-key"

        sig1 = compute_signature('{"event": "test1"}', secret)
        sig2 = compute_signature('{"event": "test2"}', secret)

        assert sig1 != sig2

    def test_different_secret_different_signature(self):
        """Test that different secrets produce different signatures."""
        from src.webhooks.dispatcher import compute_signature

        payload = '{"event": "test"}'

        sig1 = compute_signature(payload, "secret1")
        sig2 = compute_signature(payload, "secret2")

        assert sig1 != sig2

    def test_verify_signature(self):
        """Test signature verification."""
        from src.webhooks.dispatcher import compute_signature, verify_signature

        payload = '{"event": "test"}'
        secret = "my-secret-key"

        signature = compute_signature(payload, secret)

        # Valid signature
        assert verify_signature(payload, signature, secret) is True

        # Invalid signature
        assert verify_signature(payload, "sha256=invalid", secret) is False

        # Wrong payload
        assert verify_signature("different payload", signature, secret) is False

        # Wrong secret
        assert verify_signature(payload, signature, "wrong-secret") is False


class TestWebhookDispatcher:
    """Tests for webhook dispatcher."""

    def test_create_payload(self, tmp_path: Path):
        """Test creating webhook payload."""
        from src.webhooks.dispatcher import WebhookDispatcher
        from src.webhooks.storage import WebhookStorage

        storage = WebhookStorage(tmp_path)
        dispatcher = WebhookDispatcher(storage)

        payload, payload_json = dispatcher._create_payload(
            event="note.created",
            data={"path": "test.md"},
            webhook_id="test-id",
        )

        assert payload.event == "note.created"
        assert payload.data == {"path": "test.md"}
        assert payload.webhook_id == "test-id"
        assert payload.signature is None

    def test_create_payload_with_signature(self, tmp_path: Path):
        """Test creating webhook payload with signature."""
        from src.webhooks.dispatcher import WebhookDispatcher
        from src.webhooks.storage import WebhookStorage

        storage = WebhookStorage(tmp_path)
        dispatcher = WebhookDispatcher(storage)

        payload, payload_json = dispatcher._create_payload(
            event="note.created",
            data={"path": "test.md"},
            webhook_id="test-id",
            secret="my-super-secret-key",
        )

        assert payload.signature is not None
        assert payload.signature.startswith("sha256=")
