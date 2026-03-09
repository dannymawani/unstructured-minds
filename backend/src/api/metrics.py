"""Metrics API endpoint for observability."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..logging_config import get_logger
from ..middleware.request_logging import get_metrics
from .dependencies import get_user_id

router = APIRouter(tags=["metrics"])
logger = get_logger(__name__)


class LatencyMetrics(BaseModel):
    """Latency metrics."""

    average_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""

    timestamp: str
    total_requests: int
    requests_by_method: dict[str, int]
    requests_by_status: dict[int, int]
    error_count: int
    error_rate_percent: float
    latency: LatencyMetrics


class MetricsResetResponse(BaseModel):
    """Response for metrics reset."""

    success: bool
    message: str


@router.get("/metrics", response_model=MetricsResponse)
async def get_request_metrics(user_id: str = Depends(get_user_id)) -> MetricsResponse:
    """Get request metrics.

    Returns aggregated metrics about API requests including:
    - Total request count
    - Requests by HTTP method
    - Requests by status code
    - Error count and rate
    - Latency percentiles (p50, p95, p99)

    Returns:
        Current request metrics
    """
    metrics = get_metrics()
    data = metrics.to_dict()

    logger.debug(
        "metrics_requested",
        total_requests=data["total_requests"],
        error_rate=data["error_rate_percent"],
    )

    return MetricsResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_requests=data["total_requests"],
        requests_by_method=data["requests_by_method"],
        requests_by_status=data["requests_by_status"],
        error_count=data["error_count"],
        error_rate_percent=data["error_rate_percent"],
        latency=LatencyMetrics(**data["latency"]),
    )


@router.post("/metrics/reset", response_model=MetricsResetResponse)
async def reset_metrics(user_id: str = Depends(get_user_id)) -> MetricsResetResponse:
    """Reset all request metrics.

    Clears all accumulated metrics data. Use with caution in production.

    Returns:
        Success status
    """
    metrics = get_metrics()
    metrics.reset()

    logger.info("metrics_reset")

    return MetricsResetResponse(
        success=True,
        message="Metrics have been reset",
    )
