"""Settings API endpoints."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from datetime import datetime as dt

from fastapi import HTTPException

from ..config import settings


router = APIRouter(prefix="/settings", tags=["settings"])


# Settings file path
SETTINGS_FILE = settings.data_path / "settings.json"

# Default daily note path template: {YYYY}/{MM}/{YYYY}-{MM}-{DD}-daily-note
DEFAULT_DAILY_NOTE_TEMPLATE = "{YYYY}/{MM}/{YYYY}-{MM}-{DD}-daily-note"


def get_daily_note_template() -> str:
    """Get the configured daily note path template."""
    stored = _load_settings()
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


def _load_settings() -> dict:
    """Load settings from JSON file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"theme": "dark"}


def _save_settings(data: dict) -> None:
    """Save settings to JSON file."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


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
def get_settings(request: Request) -> SettingsResponse:
    """Get current application settings.

    Returns:
        Current settings (sensitive values masked)
    """
    claude = request.app.state.claude
    stored = _load_settings()

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
def update_settings(request: Request, update: SettingsUpdateRequest) -> SettingsResponse:
    """Update application settings.

    Args:
        update: Settings to update

    Returns:
        Updated settings
    """
    stored = _load_settings()

    if update.theme and update.theme in ["dark", "light"]:
        stored["theme"] = update.theme

    if update.daily_note_path_template is not None:
        tpl = update.daily_note_path_template
        # Validate template: must contain date placeholders, no path traversal
        if ".." in tpl or tpl.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid template: path traversal not allowed")
        if not all(p in tpl for p in ["{YYYY}", "{MM}", "{DD}"]):
            raise HTTPException(status_code=400, detail="Template must contain {YYYY}, {MM}, and {DD}")
        stored["daily_note_path_template"] = tpl

    if update.show_month_names is not None:
        stored["show_month_names"] = update.show_month_names

    _save_settings(stored)

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
def get_theme() -> ThemeResponse:
    """Get current theme settings.

    Returns:
        Current theme and available options
    """
    stored = _load_settings()
    return ThemeResponse(
        theme=stored.get("theme", "dark"),
        available_themes=["dark", "light"],
    )


@router.post("/theme", response_model=ThemeResponse)
def set_theme(theme: str) -> ThemeResponse:
    """Set theme preference.

    Args:
        theme: Theme name ("dark" or "light")

    Returns:
        Updated theme settings
    """
    stored = _load_settings()
    if theme in ["dark", "light"]:
        stored["theme"] = theme
        _save_settings(stored)

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
    """Get system information.

    Returns:
        System info for diagnostics
    """
    import sys
    from ..db.schema import get_table_names

    db = request.app.state.db
    tables = get_table_names(db._conn) if db and db._conn else []

    return SystemInfoResponse(
        version="0.1.0",
        python_version=sys.version.split()[0],
        database_tables=tables,
        storage_type="local",
    )
