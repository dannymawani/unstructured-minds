"""Enhanced health check endpoints for monitoring and observability."""

import time
from datetime import UTC, datetime
from enum import StrEnum

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..config import settings
from ..db import DatabaseManager
from ..logging_config import get_logger
from ..storage import StorageBackend
from .dependencies import get_db as _dep_get_db
from .dependencies import get_storage as _dep_get_storage

router = APIRouter(tags=["health"])
logger = get_logger(__name__)

# Track application start time for uptime calculation
_start_time: float | None = None


def set_start_time() -> None:
    """Set the application start time. Called during startup."""
    global _start_time
    _start_time = time.time()


def get_uptime_seconds() -> float:
    """Get application uptime in seconds."""
    if _start_time is None:
        return 0.0
    return time.time() - _start_time


class HealthStatus(StrEnum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentStatus(StrEnum):
    """Component status values."""

    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"


# =============================================================================
# Response Models
# =============================================================================


class BasicHealthResponse(BaseModel):
    """Basic health check response for load balancers."""

    status: HealthStatus
    timestamp: str = Field(description="ISO 8601 timestamp")


class ReadinessResponse(BaseModel):
    """Readiness check response - ready to serve traffic."""

    status: HealthStatus
    ready: bool
    timestamp: str
    message: str | None = None


class LivenessResponse(BaseModel):
    """Liveness check response - application is alive."""

    status: HealthStatus
    alive: bool
    timestamp: str
    uptime_seconds: float


class ComponentHealth(BaseModel):
    """Health status of a single component."""

    name: str
    status: ComponentStatus
    latency_ms: float | None = None
    message: str | None = None
    details: dict | None = None


class DetailedHealthResponse(BaseModel):
    """Detailed health response with all component statuses."""

    status: HealthStatus
    version: str
    timestamp: str
    uptime_seconds: float
    environment: str
    components: list[ComponentHealth]
    checks: dict[str, bool]


# =============================================================================
# Dependencies
# =============================================================================


def get_db(request: Request):
    """Get database manager from app state."""
    return _dep_get_db(request)


def get_storage(request: Request) -> StorageBackend:
    """Get storage backend (user-scoped in cloud mode)."""
    return _dep_get_storage(request)


def get_claude(request: Request):
    """Get Claude client from app state."""
    return request.app.state.claude


# =============================================================================
# Health Check Endpoints
# =============================================================================


@router.get("/health", response_model=BasicHealthResponse)
async def health() -> BasicHealthResponse:
    """Basic health check endpoint.

    Used by load balancers and container orchestrators for basic health status.
    This is a lightweight check that should always respond quickly.

    Returns:
        Basic health status
    """
    return BasicHealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/health/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    """Liveness probe endpoint.

    Indicates if the application is alive and running. Used by Kubernetes
    liveness probes. If this fails, the container should be restarted.

    Returns:
        Liveness status with uptime
    """
    uptime = get_uptime_seconds()
    logger.debug("liveness_check", uptime_seconds=uptime)

    return LivenessResponse(
        status=HealthStatus.HEALTHY,
        alive=True,
        timestamp=datetime.now(UTC).isoformat(),
        uptime_seconds=uptime,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> ReadinessResponse:
    """Readiness probe endpoint.

    Indicates if the application is ready to serve traffic. Used by Kubernetes
    readiness probes. Checks that critical dependencies (database, storage)
    are available.

    Returns:
        Readiness status
    """
    timestamp = datetime.now(UTC).isoformat()
    issues: list[str] = []

    # Check database
    try:
        db.execute("SELECT 1")
    except Exception as e:
        issues.append(f"Database: {str(e)}")
        logger.warning("readiness_check_failed", component="database", error=str(e))

    # Check storage
    try:
        await storage.exists("")
    except Exception as e:
        issues.append(f"Storage: {str(e)}")
        logger.warning("readiness_check_failed", component="storage", error=str(e))

    ready = len(issues) == 0
    status = HealthStatus.HEALTHY if ready else HealthStatus.UNHEALTHY
    message = None if ready else "; ".join(issues)

    logger.debug("readiness_check", ready=ready, issues=issues)

    return ReadinessResponse(
        status=status,
        ready=ready,
        timestamp=timestamp,
        message=message,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health(
    db: DatabaseManager = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    claude=Depends(get_claude),
) -> DetailedHealthResponse:
    """Detailed health check endpoint.

    Provides comprehensive health information about all system components.
    This endpoint is more expensive and should be used for debugging and
    monitoring dashboards rather than frequent health checks.

    Returns:
        Detailed health status for all components
    """
    timestamp = datetime.now(UTC).isoformat()
    components: list[ComponentHealth] = []
    checks: dict[str, bool] = {}

    # Check database
    db_status, db_latency, db_message, db_details = await _check_database(db)
    components.append(
        ComponentHealth(
            name="database",
            status=db_status,
            latency_ms=db_latency,
            message=db_message,
            details=db_details,
        )
    )
    checks["database"] = db_status == ComponentStatus.UP

    # Check storage
    storage_status, storage_latency, storage_message = await _check_storage(storage)
    components.append(
        ComponentHealth(
            name="storage",
            status=storage_status,
            latency_ms=storage_latency,
            message=storage_message,
            details={
                "vault_path": str(settings.vault_path.absolute()),
                "vault_exists": settings.vault_path.exists(),
            },
        )
    )
    checks["storage"] = storage_status == ComponentStatus.UP

    # Check Claude API
    claude_status, claude_message = _check_claude(claude)
    components.append(
        ComponentHealth(
            name="claude_api",
            status=claude_status,
            message=claude_message,
            details={"configured": claude.is_configured if claude else False},
        )
    )
    checks["claude_api"] = claude_status in (ComponentStatus.UP, ComponentStatus.DEGRADED)

    # Check file watcher (if applicable)
    watcher_status, watcher_message = _check_watcher()
    components.append(
        ComponentHealth(
            name="file_watcher",
            status=watcher_status,
            message=watcher_message,
        )
    )
    checks["file_watcher"] = watcher_status in (ComponentStatus.UP, ComponentStatus.DEGRADED)

    # Determine overall status
    critical_ok = checks["database"] and checks["storage"]
    all_ok = all(checks.values())

    if all_ok:
        overall_status = HealthStatus.HEALTHY
    elif critical_ok:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.UNHEALTHY

    logger.info(
        "detailed_health_check",
        status=overall_status,
        checks=checks,
        uptime_seconds=get_uptime_seconds(),
    )

    return DetailedHealthResponse(
        status=overall_status,
        version="0.1.0",
        timestamp=timestamp,
        uptime_seconds=get_uptime_seconds(),
        environment="development" if settings.debug else "production",
        components=components,
        checks=checks,
    )


# =============================================================================
# Component Check Helpers
# =============================================================================


async def _check_database(
    db: DatabaseManager,
) -> tuple[ComponentStatus, float | None, str | None, dict | None]:
    """Check database health.

    Returns:
        Tuple of (status, latency_ms, message, details)
    """
    try:
        from ..db.sql_compat import get_dialect

        start = time.perf_counter()
        result = db.execute("SELECT COUNT(*) as table_count FROM information_schema.tables")
        table_count = result.fetchone()[0]
        latency_ms = (time.perf_counter() - start) * 1000

        dialect = get_dialect(db)
        db_path = str(getattr(db, "db_path", "postgres")) if dialect == "duckdb" else "postgres"

        return (
            ComponentStatus.UP,
            round(latency_ms, 2),
            None,
            {
                "path": db_path,
                "table_count": table_count,
            },
        )
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return ComponentStatus.DOWN, None, str(e), None


async def _check_storage(
    storage: StorageBackend,
) -> tuple[ComponentStatus, float | None, str | None]:
    """Check storage health.

    Returns:
        Tuple of (status, latency_ms, message)
    """
    try:
        start = time.perf_counter()
        await storage.exists("")
        latency_ms = (time.perf_counter() - start) * 1000

        # Check if vault path exists
        if not settings.vault_path.exists():
            return (
                ComponentStatus.DEGRADED,
                round(latency_ms, 2),
                "Vault path does not exist",
            )

        return ComponentStatus.UP, round(latency_ms, 2), None
    except Exception as e:
        logger.error("storage_health_check_failed", error=str(e))
        return ComponentStatus.DOWN, None, str(e)


def _check_claude(claude) -> tuple[ComponentStatus, str | None]:
    """Check Claude API status.

    Returns:
        Tuple of (status, message)
    """
    if claude is None:
        return ComponentStatus.DOWN, "Claude client not initialized"

    if not claude.is_configured:
        return ComponentStatus.DEGRADED, "API key not configured"

    return ComponentStatus.UP, None


def _check_watcher() -> tuple[ComponentStatus, str | None]:
    """Check file watcher status.

    Returns:
        Tuple of (status, message)
    """
    if not settings.vault_path.exists():
        return ComponentStatus.DEGRADED, "Vault path does not exist, watcher disabled"

    # File watcher is running if vault exists
    return ComponentStatus.UP, None
