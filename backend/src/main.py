"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .logging_config import configure_logging, get_logger
from .api.routes import router
from .api.skills import router as skills_router
from .api.extraction import router as extraction_router
from .api.dashboard import router as dashboard_router
from .api.settings import router as settings_router
from .api.schemas import router as schemas_router
from .api.kanban import router as kanban_router
from .api.search import router as search_router
from .api.query import router as query_router
from .api.export import router as export_router, import_router
from .api.calendar import router as calendar_router
from .api.templates import router as templates_router
from .api.tags import router as tags_router
from .api.tasks import router as tasks_router
from .api.health import router as health_router, set_start_time
from .api.metrics import router as metrics_router
from .api.insights import router as insights_router
from .api.note_assist import router as note_assist_router
from .api.profile import router as profile_router
from .claude import ClaudeClient
from .db import DatabaseManager
from .middleware import limiter, SecurityHeadersMiddleware, RequestLoggingMiddleware
from .storage import get_storage_backend

# Configure structured logging
configure_logging(
    debug=settings.debug,
    json_logs=not settings.debug,  # JSON in production, console in dev
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Record startup time for uptime tracking
    set_start_time()

    logger.info(
        "application_starting",
        vault_path=str(settings.vault_path),
        data_path=str(settings.data_path),
        claude_enabled=settings.claude_enabled,
        debug=settings.debug,
    )

    # Initialize storage
    storage = get_storage_backend("local", base_path=settings.vault_path)
    app.state.storage = storage

    # Initialize database
    settings.data_path.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(settings.duckdb_path)
    db.connect()
    app.state.db = db
    logger.info("database_initialized", path=str(settings.duckdb_path))

    # Initialize Claude client
    claude = ClaudeClient()
    app.state.claude = claude
    logger.info("claude_client_initialized", configured=claude.is_configured)

    logger.info("application_ready")

    yield

    # Cleanup
    logger.info("application_shutting_down")
    app.state.db.close()
    logger.info("database_closed")


app = FastAPI(
    title="Unstructured Minds API",
    description="Transform natural language notes into structured, queryable data",
    version="0.1.0",
    lifespan=lifespan,
)

# =============================================================================
# Security Middleware
# =============================================================================

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request logging middleware (added first, executed last - captures all requests)
app.add_middleware(
    RequestLoggingMiddleware,
    exclude_paths={"/health", "/health/live"},  # Skip logging for frequent health checks
)

# Security headers (must be added before CORS to ensure headers are set)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# Include routes
app.include_router(router)
app.include_router(health_router)  # Enhanced health checks
app.include_router(metrics_router)  # Request metrics
app.include_router(skills_router)
app.include_router(extraction_router)
app.include_router(dashboard_router)
app.include_router(settings_router)
app.include_router(schemas_router)
app.include_router(kanban_router)
app.include_router(search_router)
app.include_router(query_router)
app.include_router(export_router)
app.include_router(import_router)
app.include_router(calendar_router)
app.include_router(templates_router)
app.include_router(tags_router)
app.include_router(tasks_router)
app.include_router(insights_router)
app.include_router(note_assist_router)
app.include_router(profile_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
