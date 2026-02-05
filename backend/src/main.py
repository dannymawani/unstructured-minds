"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .logging_config import configure_logging, get_logger
from .api.routes import router
from .api.chat import router as chat_router
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
from .api.health import router as health_router, set_start_time
from .api.metrics import router as metrics_router
from .api.insights import router as insights_router
from .api.plugins import router as plugins_router
from .api.webhooks import router as webhooks_router
from .claude import ClaudeClient
from .plugins import PluginManager
from .db import DatabaseManager
from .extraction import ExtractionPipeline
from .middleware import limiter, SecurityHeadersMiddleware, RequestLoggingMiddleware
from .storage import get_storage_backend
from .watcher import FileWatcher
from .webhooks import dispatch_event, WebhookEvent

# Configure structured logging
configure_logging(
    debug=settings.debug,
    json_logs=not settings.debug,  # JSON in production, console in dev
)
logger = get_logger(__name__)


def create_extraction_callback(
    storage,
    db: DatabaseManager,
    claude: ClaudeClient,
) -> callable:
    """Create a callback function for file change extraction.

    Args:
        storage: Storage backend
        db: Database manager
        claude: Claude client

    Returns:
        Callback function
    """

    def on_file_change(file_path: str) -> None:
        """Handle file change by triggering extraction."""
        if not claude.is_configured:
            logger.debug("extraction_skipped", file=file_path, reason="claude_not_configured")
            return

        async def extract():
            import time
            start_time = time.perf_counter()
            try:
                content_bytes = await storage.read(file_path)
                content = content_bytes.decode("utf-8")
                pipeline = ExtractionPipeline(db, claude)
                result = await pipeline.extract(file_path, content)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if result.success and result.data:
                    logger.info(
                        "extraction_completed",
                        file=file_path,
                        records_inserted=result.records_inserted,
                        duration_ms=round(duration_ms, 2),
                    )
                    # Dispatch webhook event for successful extraction
                    await dispatch_event(
                        WebhookEvent.EXTRACTION_COMPLETED.value,
                        {
                            "file_path": file_path,
                            "records_inserted": result.records_inserted,
                            "data": result.data,
                        },
                    )
                elif result.error and "Already extracted" not in result.error:
                    logger.warning(
                        "extraction_failed",
                        file=file_path,
                        error=result.error,
                        duration_ms=round(duration_ms, 2),
                    )
            except FileNotFoundError:
                logger.debug("extraction_skipped", file=file_path, reason="file_not_found")
            except Exception as e:
                logger.error("extraction_error", file=file_path, error=str(e))

        # Schedule the async extraction
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(extract())
        except RuntimeError:
            # No running loop, run synchronously
            asyncio.run(extract())

    return on_file_change


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

    # Initialize plugin system
    from pathlib import Path

    plugins_state_path = settings.data_path / "plugins.json"
    plugin_manager = PluginManager(plugins_state_path)
    app.state.plugin_manager = plugin_manager

    # Load built-in plugins from examples directory
    examples_dir = Path(__file__).parent / "plugins" / "examples"
    await plugin_manager.load_builtin_plugins(examples_dir)
    logger.info(
        "plugin_system_initialized",
        plugins_loaded=len(plugin_manager.list_plugins()),
    )

    # Initialize file watcher for auto-extraction
    watcher: Optional[FileWatcher] = None
    if settings.vault_path.exists():
        extraction_callback = create_extraction_callback(storage, db, claude)
        watcher = FileWatcher(
            vault_path=settings.vault_path,
            on_change=extraction_callback,
            debounce_seconds=1.0,
        )
        watcher.start(loop=asyncio.get_running_loop())
        app.state.watcher = watcher
        logger.info("file_watcher_started", vault_path=str(settings.vault_path))
    else:
        logger.warning("file_watcher_disabled", reason="vault_path_not_exists")

    logger.info("application_ready")

    yield

    # Cleanup
    logger.info("application_shutting_down")
    if watcher:
        watcher.stop()
        logger.info("file_watcher_stopped")
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
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],  # Expose request ID header to frontend
)

# Include routes
app.include_router(router)
app.include_router(health_router)  # Enhanced health checks
app.include_router(metrics_router)  # Request metrics
app.include_router(chat_router)
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
app.include_router(insights_router)
app.include_router(plugins_router)
app.include_router(webhooks_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
