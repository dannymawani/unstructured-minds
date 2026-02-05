"""Tests for health check endpoints."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from src.api.health import (
    set_start_time,
    get_uptime_seconds,
    HealthStatus,
    ComponentStatus,
    _check_database,
    _check_storage,
    _check_claude,
)


class TestHealthHelpers:
    """Tests for health check helper functions."""

    def test_set_start_time(self):
        """Test that start time can be set."""
        set_start_time()
        uptime = get_uptime_seconds()
        assert uptime >= 0
        assert uptime < 1  # Should be very small right after setting

    def test_get_uptime_seconds_before_set(self):
        """Test uptime returns 0 if start time not set."""
        import src.api.health as health_module
        health_module._start_time = None
        assert get_uptime_seconds() == 0.0


class TestComponentChecks:
    """Tests for individual component health checks."""

    @pytest.mark.asyncio
    async def test_check_database_healthy(self):
        """Test database check when healthy."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [10]
        mock_db.execute.return_value = mock_result
        mock_db.db_path = "/tmp/test.duckdb"

        status, latency, message, details = await _check_database(mock_db)

        assert status == ComponentStatus.UP
        assert latency is not None
        assert latency >= 0
        assert message is None
        assert details["table_count"] == 10

    @pytest.mark.asyncio
    async def test_check_database_unhealthy(self):
        """Test database check when unhealthy."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Connection failed")

        status, latency, message, details = await _check_database(mock_db)

        assert status == ComponentStatus.DOWN
        assert latency is None
        assert "Connection failed" in message
        assert details is None

    @pytest.mark.asyncio
    async def test_check_storage_healthy(self):
        """Test storage check when healthy."""
        mock_storage = AsyncMock()
        mock_storage.exists.return_value = True

        with patch("src.api.health.settings") as mock_settings:
            mock_settings.vault_path.exists.return_value = True

            status, latency, message = await _check_storage(mock_storage)

            assert status == ComponentStatus.UP
            assert latency is not None
            assert message is None

    @pytest.mark.asyncio
    async def test_check_storage_degraded(self):
        """Test storage check when vault path missing."""
        mock_storage = AsyncMock()
        mock_storage.exists.return_value = True

        with patch("src.api.health.settings") as mock_settings:
            mock_settings.vault_path.exists.return_value = False

            status, latency, message = await _check_storage(mock_storage)

            assert status == ComponentStatus.DEGRADED
            assert "Vault path does not exist" in message

    @pytest.mark.asyncio
    async def test_check_storage_unhealthy(self):
        """Test storage check when unhealthy."""
        mock_storage = AsyncMock()
        mock_storage.exists.side_effect = Exception("Storage error")

        status, latency, message = await _check_storage(mock_storage)

        assert status == ComponentStatus.DOWN
        assert "Storage error" in message

    def test_check_claude_configured(self):
        """Test Claude check when configured."""
        mock_claude = MagicMock()
        mock_claude.is_configured = True

        status, message = _check_claude(mock_claude)

        assert status == ComponentStatus.UP
        assert message is None

    def test_check_claude_not_configured(self):
        """Test Claude check when not configured."""
        mock_claude = MagicMock()
        mock_claude.is_configured = False

        status, message = _check_claude(mock_claude)

        assert status == ComponentStatus.DEGRADED
        assert "not configured" in message

    def test_check_claude_none(self):
        """Test Claude check when client is None."""
        status, message = _check_claude(None)

        assert status == ComponentStatus.DOWN
        assert "not initialized" in message


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestComponentStatus:
    """Tests for ComponentStatus enum."""

    def test_component_status_values(self):
        """Test component status enum values."""
        assert ComponentStatus.UP == "up"
        assert ComponentStatus.DOWN == "down"
        assert ComponentStatus.DEGRADED == "degraded"
