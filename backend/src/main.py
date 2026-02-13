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
from .api.exercises import router as exercises_router
from .claude import ClaudeClient
from .db import DatabaseManager, PostgresManager, init_postgres_schema
from .db.analytics_cache import AnalyticsCacheManager
from .extraction.exercise_matcher import ExerciseMatcher
from .extraction.exercise_normalizer import normalize_exercises
from .middleware import limiter, SecurityHeadersMiddleware, RequestLoggingMiddleware
from .storage import get_storage_backend
from .storage.postgres import PostgresStorage
from .storage.datastore import DataStore

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
        mode="cloud" if settings.is_cloud_mode else "local",
    )

    analytics_cache_manager = None

    if settings.is_cloud_mode:
        # ── CLOUD MODE ─────────────────────────────────────────────
        # Postgres is the source of truth for all data.
        # DuckDB (in-memory) is a disposable analytics cache.
        # Vault/data files stored in Postgres.
        pg = PostgresManager(settings.database_url, pool_min=settings.db_pool_min, pool_max=settings.db_pool_max)
        pg.connect()
        init_postgres_schema(pg, settings.default_user_id)
        app.state.db = pg

        # In-memory DuckDB for fast analytics
        analytics_db = DatabaseManager(":memory:")
        analytics_db.connect()
        app.state.analytics_db = analytics_db

        # Populate analytics cache from Postgres.
        # Short-term: cache uses default_user_id. Per-request user-scoped
        # queries go directly to Postgres via dependencies.
        analytics_cache_manager = AnalyticsCacheManager(
            pg, analytics_db, settings.default_user_id
        )
        analytics_cache_manager.init_cache_schema()
        analytics_cache_manager.refresh()
        analytics_cache_manager.start_background_refresh(interval=60)

        # Storage: default instances for startup tasks (e.g. exercise normalization).
        # Per-request user-scoped storage is created in dependencies.py.
        storage = PostgresStorage(pg, settings.default_user_id)
        data_storage = PostgresStorage(pg, settings.default_user_id, "_data")

        logger.info("database_initialized", mode="cloud", backend="postgres")
    else:
        # ── LOCAL MODE ─────────────────────────────────────────────
        # DuckDB file + local filesystem. Zero external deps.
        settings.data_path.mkdir(parents=True, exist_ok=True)
        db = DatabaseManager(settings.duckdb_path)
        db.connect()
        app.state.db = db
        app.state.analytics_db = db

        storage = get_storage_backend("local", base_path=settings.vault_path)
        data_storage = get_storage_backend("local", base_path=settings.data_path)

        logger.info("database_initialized", mode="local", path=str(settings.duckdb_path))

    app.state.storage = storage
    app.state.datastore = DataStore(data_storage)
    app.state.analytics_cache_manager = analytics_cache_manager

    # Initialize Claude client
    claude = ClaudeClient()
    app.state.claude = claude
    logger.info("claude_client_initialized", configured=claude.is_configured)

    # Initialize exercise matcher and run normalization
    from pathlib import Path
    project_root = Path(__file__).resolve().parents[2]
    shared_defs = project_root / "shared" / "exercise_definitions.json"
    exercise_defs_path = shared_defs if shared_defs.exists() else settings.data_path / "exercise_definitions.json"
    exercise_matcher = ExerciseMatcher(exercise_defs_path)
    app.state.exercise_matcher = exercise_matcher

    # Load community exercises into the matcher
    try:
        rows = app.state.db.execute(
            "SELECT exercise_key, display_name, aliases, muscle_groups, category, recovery_hours FROM community_exercises"
        ).fetchall()
        community_exercises = [
            {
                "exercise_key": r[0],
                "display_name": r[1],
                "aliases": r[2],
                "muscle_groups": r[3],
                "category": r[4],
                "recovery_hours": r[5],
            }
            for r in rows
        ]
        exercise_matcher.load_community_exercises(community_exercises)
    except Exception as e:
        logger.warning("community_exercises_load_failed", error=str(e))

    # Build user_settings_store for cloud mode
    user_settings_store = None
    if settings.is_cloud_mode:
        from .db.user_settings import UserSettingsStore
        user_settings_store = UserSettingsStore(app.state.db, settings.default_user_id)

    try:
        await normalize_exercises(
            db=app.state.db,
            matcher=exercise_matcher,
            claude=claude,
            cache_path=settings.data_path / "ai_exercise_cache.json",
            user_settings_store=user_settings_store,
        )
    except Exception as e:
        logger.warning("exercise_normalization_startup_failed", error=str(e))

    logger.info("application_ready")

    yield

    # Cleanup
    logger.info("application_shutting_down")
    if analytics_cache_manager:
        await analytics_cache_manager.stop()
        logger.info("analytics_cache_stopped")

    # Close analytics DB if it's a separate instance (cloud mode)
    if (
        hasattr(app.state, "analytics_db")
        and app.state.analytics_db is not app.state.db
    ):
        app.state.analytics_db.close()
        logger.info("analytics_database_closed")
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
app.include_router(exercises_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
