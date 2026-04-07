"""Application configuration."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Hardcoded user ID for local (single-user) mode — not configurable via env.
LOCAL_USER_ID = "local"


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

    # LLM provider (optional — app works without it, AI features disabled)
    llm_provider: Optional[str] = None  # anthropic, openai, ollama, etc.
    llm_api_key: Optional[str] = None
    llm_model_fast: Optional[str] = None
    llm_model_smart: Optional[str] = None

    # Legacy: still works for backward compatibility
    anthropic_api_key: Optional[str] = None

    # Cloud mode: explicit flag + Postgres connection string
    use_cloud: bool = False
    database_url: Optional[str] = None

    # Postgres connection pool sizing
    db_pool_min: int = 2
    db_pool_max: int = 10

    # Azure managed identity (cloud mode only)
    azure_use_managed_identity: bool = False
    azure_postgres_host: Optional[str] = None
    azure_postgres_db: str = "unstructured_minds"
    azure_postgres_user: str = "um-backend"

    # Auth mode: "none" (default), "basic", or "clerk"
    auth_mode: str = "none"
    basic_auth_username: Optional[str] = None
    basic_auth_password: Optional[str] = None

    # Clerk auth (only when auth_mode=clerk)
    clerk_secret_key: Optional[str] = None
    clerk_domain: Optional[str] = None  # e.g. "your-app.clerk.accounts.dev"

    @property
    def use_token_auth(self) -> bool:
        """True when managed identity is enabled with a Postgres host."""
        return self.azure_use_managed_identity and self.azure_postgres_host is not None

    @property
    def is_cloud_mode(self) -> bool:
        """True when USE_CLOUD=true and DATABASE_URL or managed identity is set."""
        return self.use_cloud and (self.database_url is not None or self.use_token_auth)

    @property
    def auth_enabled(self) -> bool:
        """Auth is enabled when auth_mode is not 'none', or in cloud mode for backward compat."""
        if self.auth_mode != "none":
            return True
        if self.is_cloud_mode and self.clerk_secret_key:
            return True
        return False

    @property
    def duckdb_path(self) -> Path:
        """Path to DuckDB database file."""
        return self.data_path / "unstructured.duckdb"

    @property
    def llm_enabled(self) -> bool:
        """Check if any LLM provider is configured."""
        return bool(self.llm_api_key or self.anthropic_api_key or self.llm_provider == "ollama")

    @property
    def claude_enabled(self) -> bool:
        """Backward compat alias."""
        return self.llm_enabled


settings = Settings()
