"""Community exercises and autocomplete API endpoints."""

import json
import re

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..db.sql_compat import get_dialect
from ..extraction.exercise_matcher import ExerciseMatcher
from ..logging_config import get_logger
from .dependencies import get_db as _get_primary_db

logger = get_logger(__name__)

router = APIRouter(prefix="/exercises", tags=["exercises"])


def get_db(request: Request):
    """Get primary database for community exercises (persisted, not analytics cache)."""
    return _get_primary_db(request)


def get_exercise_matcher(request: Request) -> ExerciseMatcher:
    """Get exercise matcher from app state."""
    return request.app.state.exercise_matcher


# ── Models ──────────────────────────────────────────────────────────


class CommunityExerciseCreate(BaseModel):
    """Request to contribute a new exercise to the community pool."""

    name: str = Field(..., min_length=1, max_length=200)
    muscle_groups: list[str] = Field(default_factory=list)
    category: str = "other"
    recovery_hours: int = Field(default=48, ge=12, le=168)


class CommunityExerciseResponse(BaseModel):
    """Response after contributing an exercise."""

    exercise_key: str
    display_name: str
    message: str


class SuggestResult(BaseModel):
    """Single autocomplete suggestion."""

    name: str
    category: str | None = None
    muscle_groups: list[str] = []
    source: str  # "builtin" or "community"


class SuggestResponse(BaseModel):
    """Response for exercise autocomplete."""

    results: list[SuggestResult]


# ── Helpers ─────────────────────────────────────────────────────────


def _make_exercise_key(name: str) -> str:
    """Convert a display name to a snake_case exercise key."""
    key = name.strip().lower()
    key = re.sub(r"[^a-z0-9\s]", "", key)
    key = re.sub(r"\s+", "_", key)
    return key


def _get_builtin_keys(matcher: ExerciseMatcher) -> set[str]:
    """Get the set of all builtin canonical names (lowercased)."""
    return {name.lower() for name in matcher.canonical_names}


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/community", status_code=201, response_model=CommunityExerciseResponse)
async def contribute_exercise(
    body: CommunityExerciseCreate,
    request: Request,
    db=Depends(get_db),
    matcher: ExerciseMatcher = Depends(get_exercise_matcher),
) -> CommunityExerciseResponse:
    """Contribute a new exercise to the shared community pool.

    Only non-identifying metadata is stored — no user IDs.
    The exercise must not already exist in builtins or community.
    """
    display_name = body.name.strip().title()
    exercise_key = _make_exercise_key(display_name)

    # Check builtins
    canonical, confidence = matcher.match(display_name)
    if confidence >= ExerciseMatcher.FUZZY_THRESHOLD:
        return CommunityExerciseResponse(
            exercise_key=_make_exercise_key(canonical),
            display_name=canonical,
            message=f"Exercise already exists as '{canonical}'",
        )

    # Check community table for duplicates
    dialect = get_dialect(db)
    if dialect == "postgres":
        existing = db.execute(
            "SELECT exercise_key FROM community_exercises WHERE exercise_key = %s",
            [exercise_key],
        ).fetchone()
    else:
        existing = db.execute(
            "SELECT exercise_key FROM community_exercises WHERE exercise_key = ?",
            [exercise_key],
        ).fetchone()

    if existing:
        return CommunityExerciseResponse(
            exercise_key=exercise_key,
            display_name=display_name,
            message="Exercise already exists in community pool",
        )

    # Auto-fill muscle groups via Claude if not provided
    muscle_groups = body.muscle_groups
    category = body.category
    recovery_hours = body.recovery_hours
    if not muscle_groups:
        claude = getattr(request.app.state, "claude", None)
        if claude and claude.is_configured:
            try:
                all_meta = [matcher.get_metadata(n) for n in matcher.canonical_names]
                known_muscles = sorted({mg for m in all_meta for mg in m["muscle_groups"]})
                known_cats = sorted({m["category"] for m in all_meta})
                results = await claude.label_new_exercises(
                    exercise_names=[display_name],
                    known_muscle_groups=known_muscles,
                    known_categories=known_cats,
                )
                if results and results[0].get("is_exercise", True):
                    muscle_groups = results[0].get("muscle_groups", [])
                    category = results[0].get("category", category)
                    recovery_hours = results[0].get("recovery_hours", recovery_hours)
                    logger.info("auto_filled_community_exercise", name=display_name, muscle_groups=muscle_groups)
            except Exception as e:
                logger.warning("auto_fill_exercise_failed", name=display_name, error=str(e))

    # Insert
    aliases_val = json.dumps([])
    muscle_groups_val = json.dumps(muscle_groups) if muscle_groups else json.dumps([])

    if dialect == "postgres":
        db.execute(
            """
            INSERT INTO community_exercises (exercise_key, display_name, aliases, muscle_groups, category, recovery_hours)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [exercise_key, display_name, aliases_val, muscle_groups_val, category, recovery_hours],
        )
    else:
        db.execute(
            """
            INSERT INTO community_exercises (exercise_key, display_name, aliases, muscle_groups, category, recovery_hours)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [exercise_key, display_name, aliases_val, muscle_groups_val, category, recovery_hours],
        )

    # Inject into in-memory matcher so it's immediately available
    matcher.load_community_exercises([{
        "exercise_key": exercise_key,
        "display_name": display_name,
        "aliases": [],
        "muscle_groups": muscle_groups,
        "category": category,
        "recovery_hours": recovery_hours,
    }])

    logger.info("community_exercise_contributed", key=exercise_key, name=display_name)

    return CommunityExerciseResponse(
        exercise_key=exercise_key,
        display_name=display_name,
        message=f"Exercise '{display_name}' shared with the community",
    )


@router.get("/suggest", response_model=SuggestResponse)
def suggest_exercises(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
    request: Request = None,
    db=Depends(get_db),
    matcher: ExerciseMatcher = Depends(get_exercise_matcher),
) -> SuggestResponse:
    """Autocomplete/suggest exercises from builtins + community.

    Returns matching exercise names with source annotation.
    """
    suggestions = matcher.suggest(q, limit=limit)
    _get_builtin_keys(matcher)

    # Load community exercises for metadata annotation
    get_dialect(db)
    community_map: dict[str, dict] = {}
    try:
        rows = db.execute("SELECT exercise_key, display_name, muscle_groups, category FROM community_exercises").fetchall()
        for row in rows:
            muscle_groups = row[2]
            if isinstance(muscle_groups, str):
                try:
                    muscle_groups = json.loads(muscle_groups)
                except (json.JSONDecodeError, TypeError):
                    muscle_groups = []
            community_map[row[1].lower()] = {
                "muscle_groups": muscle_groups or [],
                "category": row[3] or "other",
            }
    except Exception as e:
        logger.warning("community_exercises_metadata_load_failed", error=str(e))

    results = []
    for s in suggestions:
        name = s["name"]
        name_lower = name.lower()
        if name_lower in community_map:
            info = community_map[name_lower]
            results.append(SuggestResult(
                name=name,
                category=info["category"],
                muscle_groups=info["muscle_groups"],
                source="community",
            ))
        else:
            results.append(SuggestResult(
                name=name,
                source="builtin",
            ))

    return SuggestResponse(results=results)
