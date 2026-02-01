"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api.routes import router
from .db import DatabaseManager
from .storage import get_storage_backend

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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

    yield

    # Cleanup
    logger.info("Shutting down")
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
