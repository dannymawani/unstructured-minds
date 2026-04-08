"""Request logging middleware with request ID tracing and metrics."""

import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variable for request ID
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_CTX_KEY = "request_id"

logger = structlog.get_logger(__name__)


@dataclass
class RequestMetrics:
    """Container for request metrics."""

    total_requests: int = 0
    requests_by_method: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    requests_by_status: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    requests_by_path: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    total_latency_ms: float = 0.0
    error_count: int = 0

    # For percentile calculations
    latencies: list[float] = field(default_factory=list)
    max_latencies_stored: int = 10000

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Record a request for metrics."""
        self.total_requests += 1
        self.requests_by_method[method] += 1
        self.requests_by_status[status_code] += 1
        self.requests_by_path[path] += 1
        self.total_latency_ms += latency_ms

        if status_code >= 400:
            self.error_count += 1

        # Store latency for percentile calculation (with limit)
        if len(self.latencies) < self.max_latencies_stored:
            self.latencies.append(latency_ms)
        else:
            # Replace oldest entry (simple ring buffer)
            idx = self.total_requests % self.max_latencies_stored
            self.latencies[idx] = latency_ms

    def get_percentile(self, percentile: float) -> float | None:
        """Calculate latency percentile.

        Args:
            percentile: Percentile value (0-100)

        Returns:
            Latency value at the given percentile, or None if no data
        """
        if not self.latencies:
            return None

        sorted_latencies = sorted(self.latencies)
        index = int((len(sorted_latencies) - 1) * percentile / 100)
        index = min(index, len(sorted_latencies) - 1)
        return sorted_latencies[index]

    def get_average_latency(self) -> float | None:
        """Get average latency in ms."""
        if self.total_requests == 0:
            return None
        return self.total_latency_ms / self.total_requests

    def get_error_rate(self) -> float:
        """Get error rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests) * 100

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for API response."""
        return {
            "total_requests": self.total_requests,
            "requests_by_method": dict(self.requests_by_method),
            "requests_by_status": dict(self.requests_by_status),
            "error_count": self.error_count,
            "error_rate_percent": round(self.get_error_rate(), 2),
            "latency": {
                "average_ms": round(self.get_average_latency() or 0, 2),
                "p50_ms": round(self.get_percentile(50) or 0, 2),
                "p95_ms": round(self.get_percentile(95) or 0, 2),
                "p99_ms": round(self.get_percentile(99) or 0, 2),
            },
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_requests = 0
        self.requests_by_method.clear()
        self.requests_by_status.clear()
        self.requests_by_path.clear()
        self.total_latency_ms = 0.0
        self.error_count = 0
        self.latencies.clear()


# Global metrics instance
_metrics = RequestMetrics()


def get_metrics() -> RequestMetrics:
    """Get the global request metrics instance."""
    return _metrics


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging with request ID tracing.

    Features:
    - Generates or propagates request IDs for distributed tracing
    - Logs request start and completion with structured data
    - Records request metrics (count, latency, errors)
    - Adds request ID to response headers
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: set[str] | None = None,
        log_request_body: bool = False,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application
            exclude_paths: Paths to exclude from logging (e.g., health checks)
            log_request_body: Whether to log request bodies (use with caution)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or {"/health", "/health/live"}
        self.log_request_body = log_request_body

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request with logging and metrics.

        Args:
            request: The incoming request
            call_next: The next middleware/handler

        Returns:
            The response
        """
        # Generate or extract request ID
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Store request ID in request state for access in handlers
        request.state.request_id = request_id

        # Bind request ID to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Extract request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        # Check if we should skip detailed logging for this path
        skip_logging = path in self.exclude_paths

        # Log request start (for non-excluded paths)
        if not skip_logging:
            log_data = {
                "method": method,
                "path": path,
                "client_ip": client_host,
            }
            if user_agent:
                log_data["user_agent"] = user_agent[:100]  # Truncate long user agents

            logger.info("request_started", **log_data)

        # Process request and measure duration
        start_time = time.perf_counter()
        status_code = 500  # Default in case of unhandled exception

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Log exception and re-raise
            logger.exception(
                "request_exception",
                method=method,
                path=path,
                error=str(e),
            )
            raise
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics
            # Normalize path for metrics (remove IDs to group endpoints)
            normalized_path = _normalize_path(path)
            _metrics.record_request(method, normalized_path, status_code, duration_ms)

            # Log request completion (for non-excluded paths)
            if not skip_logging:
                log_level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
                getattr(logger, log_level)(
                    "request_completed",
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=round(duration_ms, 2),
                )

        # Add request ID to response headers
        response.headers[REQUEST_ID_HEADER] = request_id

        return response


def _normalize_path(path: str) -> str:
    """Normalize path for metrics grouping.

    Replaces dynamic segments (UUIDs, dates, numbers) with placeholders.

    Args:
        path: The request path

    Returns:
        Normalized path
    """
    import re

    # Replace UUIDs
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
        flags=re.IGNORECASE,
    )

    # Replace dates (YYYY-MM-DD)
    path = re.sub(r"\d{4}-\d{2}-\d{2}", "{date}", path)

    # Replace numeric IDs
    path = re.sub(r"/\d+(/|$)", "/{id}\\1", path)

    return path
