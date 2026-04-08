"""Tests for request metrics."""

import pytest

from src.middleware.request_logging import (
    RequestMetrics,
    get_metrics,
    _normalize_path,
)


class TestRequestMetrics:
    """Tests for RequestMetrics class."""

    def test_initial_state(self):
        """Test metrics start at zero."""
        metrics = RequestMetrics()
        assert metrics.total_requests == 0
        assert metrics.error_count == 0
        assert metrics.total_latency_ms == 0.0
        assert len(metrics.latencies) == 0

    def test_record_request(self):
        """Test recording a request."""
        metrics = RequestMetrics()
        metrics.record_request("GET", "/api/notes", 200, 50.0)

        assert metrics.total_requests == 1
        assert metrics.requests_by_method["GET"] == 1
        assert metrics.requests_by_status[200] == 1
        assert metrics.requests_by_path["/api/notes"] == 1
        assert metrics.total_latency_ms == 50.0
        assert metrics.error_count == 0

    def test_record_error_request(self):
        """Test recording an error request."""
        metrics = RequestMetrics()
        metrics.record_request("POST", "/api/notes", 500, 100.0)

        assert metrics.total_requests == 1
        assert metrics.error_count == 1
        assert metrics.requests_by_status[500] == 1

    def test_record_4xx_error(self):
        """Test recording a 4xx error."""
        metrics = RequestMetrics()
        metrics.record_request("GET", "/api/notes/123", 404, 10.0)

        assert metrics.error_count == 1

    def test_get_average_latency(self):
        """Test average latency calculation."""
        metrics = RequestMetrics()
        metrics.record_request("GET", "/test", 200, 100.0)
        metrics.record_request("GET", "/test", 200, 200.0)
        metrics.record_request("GET", "/test", 200, 300.0)

        assert metrics.get_average_latency() == 200.0

    def test_get_average_latency_no_requests(self):
        """Test average latency with no requests."""
        metrics = RequestMetrics()
        assert metrics.get_average_latency() is None

    def test_get_error_rate(self):
        """Test error rate calculation."""
        metrics = RequestMetrics()
        metrics.record_request("GET", "/test", 200, 10.0)
        metrics.record_request("GET", "/test", 200, 10.0)
        metrics.record_request("GET", "/test", 500, 10.0)
        metrics.record_request("GET", "/test", 404, 10.0)

        assert metrics.get_error_rate() == 50.0  # 2 errors out of 4

    def test_get_error_rate_no_requests(self):
        """Test error rate with no requests."""
        metrics = RequestMetrics()
        assert metrics.get_error_rate() == 0.0

    def test_get_percentile(self):
        """Test percentile calculation."""
        metrics = RequestMetrics()
        # Add 100 requests with latencies 1-100ms
        for i in range(1, 101):
            metrics.latencies.append(float(i))

        assert metrics.get_percentile(50) == 50.0
        assert metrics.get_percentile(95) == 95.0
        assert metrics.get_percentile(99) == 99.0

    def test_get_percentile_no_data(self):
        """Test percentile with no data."""
        metrics = RequestMetrics()
        assert metrics.get_percentile(50) is None

    def test_reset(self):
        """Test resetting metrics."""
        metrics = RequestMetrics()
        metrics.record_request("GET", "/test", 200, 100.0)
        metrics.record_request("POST", "/test", 500, 50.0)

        metrics.reset()

        assert metrics.total_requests == 0
        assert metrics.error_count == 0
        assert metrics.total_latency_ms == 0.0
        assert len(metrics.latencies) == 0
        assert len(metrics.requests_by_method) == 0
        assert len(metrics.requests_by_status) == 0

    def test_to_dict(self):
        """Test converting metrics to dict."""
        metrics = RequestMetrics()
        metrics.record_request("GET", "/test", 200, 100.0)
        metrics.record_request("POST", "/test", 500, 200.0)

        data = metrics.to_dict()

        assert data["total_requests"] == 2
        assert data["error_count"] == 1
        assert data["error_rate_percent"] == 50.0
        assert "latency" in data
        assert "average_ms" in data["latency"]
        assert "p50_ms" in data["latency"]
        assert "p95_ms" in data["latency"]
        assert "p99_ms" in data["latency"]

    def test_latency_ring_buffer(self):
        """Test latency ring buffer behavior."""
        metrics = RequestMetrics()
        metrics.max_latencies_stored = 10

        # Record more requests than the buffer size
        for i in range(15):
            metrics.record_request("GET", "/test", 200, float(i))

        # Should only store max_latencies_stored entries
        assert len(metrics.latencies) == 10


class TestNormalizePath:
    """Tests for path normalization."""

    def test_normalize_uuid(self):
        """Test UUID normalization."""
        path = "/api/notes/550e8400-e29b-41d4-a716-446655440000"
        assert _normalize_path(path) == "/api/notes/{id}"

    def test_normalize_date(self):
        """Test date normalization."""
        path = "/api/notes/2026-01-15"
        assert _normalize_path(path) == "/api/notes/{date}"

    def test_normalize_numeric_id(self):
        """Test numeric ID normalization."""
        path = "/api/users/123/posts"
        assert _normalize_path(path) == "/api/users/{id}/posts"

    def test_normalize_combined(self):
        """Test combined normalizations."""
        path = "/api/users/123/notes/2026-01-15"
        normalized = _normalize_path(path)
        assert "{id}" in normalized
        assert "{date}" in normalized

    def test_no_normalization_needed(self):
        """Test path that needs no normalization."""
        path = "/health"
        assert _normalize_path(path) == "/health"


class TestGetMetrics:
    """Tests for global metrics getter."""

    def test_get_metrics_returns_same_instance(self):
        """Test that get_metrics returns the same instance."""
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2
