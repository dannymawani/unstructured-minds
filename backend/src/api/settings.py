"""Settings API endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from datetime import datetime as dt

from fastapi import HTTPException

from ..config import settings
from ..db.sql_compat import get_dialect
from ..db.user_settings import UserSettingsStore
from ..storage.datastore import DataStore
from .dependencies import get_user_id, get_datastore as _dep_get_datastore


router = APIRouter(prefix="/settings", tags=["settings"])


SETTINGS_PATH = "settings.json"

# Default daily note path template: {YYYY}/{MM}/{YYYY}-{MM}-{DD}-daily-note
DEFAULT_DAILY_NOTE_TEMPLATE = "{YYYY}/{MM}/{YYYY}-{MM}-{DD}-daily-note"


# ---- Sync helpers (used by resolve_daily_note_path which is called synchronously) ----

# Settings file path for sync fallback
SETTINGS_FILE = settings.data_path / "settings.json"


def _load_settings_sync() -> dict:
    """Load settings from JSON file (sync, for use outside request context)."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"theme": "dark"}


def get_daily_note_template() -> str:
    """Get the configured daily note path template."""
    stored = _load_settings_sync()
    return stored.get("daily_note_path_template", DEFAULT_DAILY_NOTE_TEMPLATE)


def resolve_daily_note_path(date_str: str, template: Optional[str] = None) -> str:
    """Resolve a daily note path template for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format
        template: Path template (uses stored setting if None)

    Returns:
        Resolved file path with .md extension
    """
    if template is None:
        template = get_daily_note_template()
    date = dt.strptime(date_str, "%Y-%m-%d")
    path = template.replace("{YYYY}", date.strftime("%Y"))
    path = path.replace("{MM}", date.strftime("%m"))
    path = path.replace("{DD}", date.strftime("%d"))
    return path + ".md"


# ---- Async helpers (used by endpoints) ----


def _get_user_settings_store(request: Request, user_id: str):
    """Get UserSettingsStore if running in cloud mode, else None."""
    db = request.app.state.db
    if get_dialect(db) == "postgres":
        return UserSettingsStore(db, user_id)
    return None


async def _load_settings(datastore: DataStore, request: Request = None, user_id: str = None) -> dict:
    """Load settings from Postgres (cloud) or DataStore (local)."""
    if request and user_id:
        store = _get_user_settings_store(request, user_id)
        if store:
            data = store.get("settings")
            if data is not None:
                return data
            return {"theme": "dark"}

    data = await datastore.read_json(SETTINGS_PATH)
    if data is not None:
        return data
    return {"theme": "dark"}


async def _save_settings(datastore: DataStore, data: dict, request: Request = None, user_id: str = None) -> None:
    """Save settings to Postgres (cloud) or DataStore (local)."""
    if request and user_id:
        store = _get_user_settings_store(request, user_id)
        if store:
            store.set("settings", data)
            return

    await datastore.write_json(SETTINGS_PATH, data)


class SettingsResponse(BaseModel):
    """Current settings response."""

    vault_path: str
    data_path: str
    claude_enabled: bool
    claude_configured: bool
    api_key_set: bool
    theme: str
    daily_note_path_template: str
    show_month_names: bool


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""

    theme: Optional[str] = None
    daily_note_path_template: Optional[str] = None
    show_month_names: Optional[bool] = None


class ThemeResponse(BaseModel):
    """Theme settings response."""

    theme: str
    available_themes: list[str]


@router.get("", response_model=SettingsResponse)
async def get_settings(request: Request, user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> SettingsResponse:
    """Get current application settings."""
    claude = request.app.state.claude
    stored = await _load_settings(datastore, request, user_id)

    return SettingsResponse(
        vault_path=str(settings.vault_path),
        data_path=str(settings.data_path),
        claude_enabled=settings.claude_enabled,
        claude_configured=claude.is_configured if claude else False,
        api_key_set=bool(settings.anthropic_api_key),
        theme=stored.get("theme", "dark"),
        daily_note_path_template=stored.get("daily_note_path_template", DEFAULT_DAILY_NOTE_TEMPLATE),
        show_month_names=stored.get("show_month_names", False),
    )


@router.post("", response_model=SettingsResponse)
async def update_settings(request: Request, update: SettingsUpdateRequest, user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> SettingsResponse:
    """Update application settings."""
    stored = await _load_settings(datastore, request, user_id)

    if update.theme and update.theme in ["dark", "light"]:
        stored["theme"] = update.theme

    if update.daily_note_path_template is not None:
        tpl = update.daily_note_path_template
        if ".." in tpl or tpl.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid template: path traversal not allowed")
        if not all(p in tpl for p in ["{YYYY}", "{MM}", "{DD}"]):
            raise HTTPException(status_code=400, detail="Template must contain {YYYY}, {MM}, and {DD}")
        stored["daily_note_path_template"] = tpl

    if update.show_month_names is not None:
        stored["show_month_names"] = update.show_month_names

    await _save_settings(datastore, stored, request, user_id)

    claude = request.app.state.claude
    return SettingsResponse(
        vault_path=str(settings.vault_path),
        data_path=str(settings.data_path),
        claude_enabled=settings.claude_enabled,
        claude_configured=claude.is_configured if claude else False,
        api_key_set=bool(settings.anthropic_api_key),
        theme=stored.get("theme", "dark"),
        daily_note_path_template=stored.get("daily_note_path_template", DEFAULT_DAILY_NOTE_TEMPLATE),
        show_month_names=stored.get("show_month_names", False),
    )


@router.get("/theme", response_model=ThemeResponse)
async def get_theme(request: Request, user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> ThemeResponse:
    """Get current theme settings."""
    stored = await _load_settings(datastore, request, user_id)
    return ThemeResponse(
        theme=stored.get("theme", "dark"),
        available_themes=["dark", "light"],
    )


@router.post("/theme", response_model=ThemeResponse)
async def set_theme(request: Request, theme: str, user_id: str = Depends(get_user_id), datastore: DataStore = Depends(_dep_get_datastore)) -> ThemeResponse:
    """Set theme preference."""
    stored = await _load_settings(datastore, request, user_id)
    if theme in ["dark", "light"]:
        stored["theme"] = theme
        await _save_settings(datastore, stored, request, user_id)

    return ThemeResponse(
        theme=stored.get("theme", "dark"),
        available_themes=["dark", "light"],
    )


class SystemInfoResponse(BaseModel):
    """System information response."""

    version: str
    python_version: str
    database_tables: list[str]
    storage_type: str


@router.get("/system", response_model=SystemInfoResponse)
def get_system_info(request: Request) -> SystemInfoResponse:
    """Get system information."""
    import sys

    db = request.app.state.db
    tables: list[str] = []

    if get_dialect(db) == "postgres":
        # Postgres: query information_schema for table names
        try:
            result = db.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            tables = [row[0] for row in result.fetchall()]
        except Exception:
            pass
    else:
        from ..db.schema import get_table_names
        tables = get_table_names(db._conn) if db and getattr(db, "_conn", None) else []

    return SystemInfoResponse(
        version="0.1.0",
        python_version=sys.version.split()[0],
        database_tables=tables,
        storage_type="postgres" if settings.is_cloud_mode else "local",
    )
