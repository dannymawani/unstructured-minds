"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api.routes import router
from .api.chat import router as chat_router
from .api.skills import router as skills_router
from .api.extraction import router as extraction_router
from .claude import ClaudeClient
from .db import DatabaseManager
from .extraction import ExtractionPipeline
from .storage import get_storage_backend
from .watcher import FileWatcher

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
            logger.debug(f"Skipping extraction for {file_path}: Claude not configured")
            return

        async def extract():
            try:
                content_bytes = await storage.read(file_path)
                content = content_bytes.decode("utf-8")
                pipeline = ExtractionPipeline(db, claude)
                result = await pipeline.extract(file_path, content)
                if result.success and result.data:
                    logger.info(
                        f"Extracted data from {file_path}: {result.records_inserted}"
                    )
                elif result.error and "Already extracted" not in result.error:
                    logger.warning(f"Extraction failed for {file_path}: {result.error}")
            except FileNotFoundError:
                logger.debug(f"File not found (may have been deleted): {file_path}")
            except Exception as e:
                logger.error(f"Error extracting {file_path}: {e}")

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
    logger.info("Starting Unstructured Minds API")
    logger.info(f"Vault path: {settings.vault_path}")
    logger.info(f"Data path: {settings.data_path}")
    logger.info(f"Claude enabled: {settings.claude_enabled}")

    # Initialize storage
    storage = get_storage_backend("local", base_path=settings.vault_path)
    app.state.storage = storage

    # Initialize database
    settings.data_path.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(settings.duckdb_path)
    db.connect()
    app.state.db = db
    logger.info(f"Database initialized at {settings.duckdb_path}")

    # Initialize Claude client
    claude = ClaudeClient()
    app.state.claude = claude
    logger.info(f"Claude client initialized (configured: {claude.is_configured})")

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
        logger.info("File watcher started for auto-extraction")
    else:
        logger.warning(f"Vault path does not exist, file watcher disabled")

    yield

    # Cleanup
    logger.info("Shutting down")
    if watcher:
        watcher.stop()
        logger.info("File watcher stopped")
    app.state.db.close()


app = FastAPI(
    title="Unstructured Minds API",
    description="Transform natural language notes into structured, queryable data",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)
app.include_router(chat_router)
app.include_router(skills_router)
app.include_router(extraction_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
