"""Application configuration."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str:
    """Find .env file in current dir or project root (parent of backend/)."""
    for candidate in [Path(".env"), Path(__file__).resolve().parents[2] / ".env"]:
        if candidate.exists():
            return str(candidate)
    return ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    vault_path: Path = Path("../vault")
    data_path: Path = Path("../data")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Claude API (optional)
    anthropic_api_key: Optional[str] = None

    # Cloud mode: explicit flag + Postgres connection string
    use_cloud: bool = True
    database_url: Optional[str] = None
    default_user_id: str = "00000000-0000-0000-0000-000000000001"

    # Postgres connection pool sizing
    db_pool_min: int = 2
    db_pool_max: int = 10

    # Auth (Clerk) — optional, app works without it
    clerk_secret_key: Optional[str] = None
    clerk_domain: Optional[str] = None  # e.g. "your-app.clerk.accounts.dev"

    @property
    def is_cloud_mode(self) -> bool:
        """True when USE_CLOUD=true and DATABASE_URL is set."""
        return self.use_cloud and self.database_url is not None

    @property
    def auth_enabled(self) -> bool:
        """True when Clerk credentials are configured."""
        return self.clerk_secret_key is not None and self.clerk_domain is not None

    @property
    def duckdb_path(self) -> Path:
        """Path to DuckDB database file."""
        return self.data_path / "unstructured.duckdb"

    @property
    def claude_enabled(self) -> bool:
        """Check if Claude API is configured."""
        return self.anthropic_api_key is not None


settings = Settings()
