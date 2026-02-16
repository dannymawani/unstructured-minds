"""Onboarding API endpoints for demo data management."""

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..config import settings
from ..db.sql_compat import get_dialect, placeholder
from ..db.user_settings import UserSettingsStore
from ..onboarding.constants import DEMO_SOURCE_FILE, ONBOARDING_SETTINGS_KEY
from ..onboarding.lifecycle import (
    check_graduation,
    clear_all_demo_data,
    get_demo_data_count,
    get_real_data_count,
)
from ..onboarding.seed import seed_demo_data
from .dependencies import get_analytics_db, get_user_id

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Dependency helpers (must be above all endpoint definitions) ──────────────


def get_db(request: Request, _user_id: str = Depends(get_user_id)):
    """Get primary database for onboarding writes.

    Depends on get_user_id to ensure the analytics cache is populated
    on the first authenticated request (cloud mode).
    """
    return request.app.state.db


# ── Response models ──────────────────────────────────────────────────────────


class OnboardingStatus(BaseModel):
    is_new_user: bool
    demo_active: bool
    onboarding_completed: bool
    demo_data_count: int
    real_data_count: int


class SeedResponse(BaseModel):
    success: bool
    rows_inserted: dict[str, int]


class ClearResponse(BaseModel):
    success: bool
    rows_deleted: int


class CompleteResponse(BaseModel):
    success: bool


# ── Settings helpers ─────────────────────────────────────────────────────────


def _get_onboarding_state(db, user_id: str) -> dict | None:
    """Read onboarding state from user_settings (cloud) or settings.json (local)."""
    if settings.is_cloud_mode:
        store = UserSettingsStore(db, user_id)
        return store.get(ONBOARDING_SETTINGS_KEY)
    else:
        # Local mode: read from data/settings.json via sync fallback
        import json
        settings_file = settings.data_path / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    data = json.load(f)
                return data.get(ONBOARDING_SETTINGS_KEY)
            except (json.JSONDecodeError, IOError):
                pass
        return None


def _set_onboarding_state(db, user_id: str, state: dict) -> None:
    """Write onboarding state to user_settings (cloud) or settings.json (local)."""
    if settings.is_cloud_mode:
        store = UserSettingsStore(db, user_id)
        store.set(ONBOARDING_SETTINGS_KEY, state)
    else:
        import json
        settings_file = settings.data_path / "settings.json"
        data = {}
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        data[ONBOARDING_SETTINGS_KEY] = state
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_file, "w") as f:
            json.dump(data, f, indent=2)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/status", response_model=OnboardingStatus)
def get_onboarding_status(
    db=Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Return onboarding status for the current user.

    Checks if user is new, whether demo data is active, and data counts.
    Also triggers auto-graduation if the user has enough real data.
    """
    state = _get_onboarding_state(db, user_id)
    demo_count = get_demo_data_count(db, user_id)
    real_count = get_real_data_count(db, user_id)

    onboarding_completed = bool(state and state.get("completed"))
    demo_active = demo_count > 0

    # Auto-graduate: if user has enough real data, clear remaining demo
    if demo_active and check_graduation(db, user_id):
        clear_all_demo_data(db, user_id)
        demo_count = 0
        demo_active = False
        if state:
            state["graduated"] = True
            state["graduated_at"] = datetime.now().isoformat()
            _set_onboarding_state(db, user_id, state)
        _refresh_analytics_cache(db, user_id)

    # New user: no onboarding state AND no data at all
    is_new_user = state is None and demo_count == 0 and real_count == 0

    return OnboardingStatus(
        is_new_user=is_new_user,
        demo_active=demo_active,
        onboarding_completed=onboarding_completed,
        demo_data_count=demo_count,
        real_data_count=real_count,
    )


@router.post("/seed", response_model=SeedResponse)
def seed_demo(
    request: Request,
    db=Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Insert demo data for the current user. Idempotent."""
    counts = seed_demo_data(db, user_id)

    # Record onboarding state
    state = _get_onboarding_state(db, user_id) or {}
    state["seeded_at"] = datetime.now().isoformat()
    state["completed"] = False
    _set_onboarding_state(db, user_id, state)

    _refresh_analytics_cache(request, user_id)

    return SeedResponse(success=True, rows_inserted=counts)


@router.post("/clear-demo", response_model=ClearResponse)
def clear_demo(
    request: Request,
    db=Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Delete all demo data for the current user."""
    deleted = clear_all_demo_data(db, user_id)

    state = _get_onboarding_state(db, user_id) or {}
    state["cleared_at"] = datetime.now().isoformat()
    _set_onboarding_state(db, user_id, state)

    _refresh_analytics_cache(request, user_id)

    return ClearResponse(success=True, rows_deleted=deleted)


@router.post("/complete", response_model=CompleteResponse)
def complete_onboarding(
    db=Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Mark onboarding as completed (user dismissed it)."""
    state = _get_onboarding_state(db, user_id) or {}
    state["completed"] = True
    state["completed_at"] = datetime.now().isoformat()
    _set_onboarding_state(db, user_id, state)

    return CompleteResponse(success=True)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _refresh_analytics_cache(request_or_db, user_id: str) -> None:
    """Refresh the analytics cache after demo data changes (cloud mode only)."""
    # Accept either a Request or a db object — need the Request for app.state
    request = request_or_db if hasattr(request_or_db, "app") else None
    if request is None:
        return
    cache_mgr = getattr(request.app.state, "analytics_cache_manager", None)
    if cache_mgr:
        cache_mgr.refresh(user_id=user_id)
