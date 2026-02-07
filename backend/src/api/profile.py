"""Life Profile API endpoints."""

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import settings


router = APIRouter(prefix="/profile", tags=["profile"])

PROFILE_FILE = settings.data_path / "life_profile.json"


# --- Pydantic Models ---


class Overview(BaseModel):
    name: str = ""
    age: Optional[int] = None
    location: str = ""
    company: str = ""
    role: str = ""
    summary: str = ""


class PersonalSection(BaseModel):
    family: list[str] = Field(default_factory=list)
    friends: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    notes: str = ""


class WorkSection(BaseModel):
    role: str = ""
    company: str = ""
    projects: list[str] = Field(default_factory=list)
    colleagues: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    notes: str = ""


class TrainingSection(BaseModel):
    disciplines: list[str] = Field(default_factory=list)
    current_lifts: dict[str, str] = Field(default_factory=dict)
    recovery: str = ""
    goals: list[str] = Field(default_factory=list)
    notes: str = ""


class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: str = ""
    description: str = ""
    status: str = "active"
    target_date: Optional[str] = None
    progress: Optional[int] = None


class LifeProfile(BaseModel):
    overview: Overview = Field(default_factory=Overview)
    personal: PersonalSection = Field(default_factory=PersonalSection)
    work: WorkSection = Field(default_factory=WorkSection)
    training: TrainingSection = Field(default_factory=TrainingSection)
    goals: list[Goal] = Field(default_factory=list)


class ReviewCreateRequest(BaseModel):
    period_start: str
    period_end: str
    key_wins: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    work_highlights: str = ""
    training_summary: str = ""
    personal_wins: list[str] = Field(default_factory=list)
    health_metrics: Optional[dict] = None
    goal_progress: Optional[dict] = None
    focus_next: list[str] = Field(default_factory=list)


class ReviewUpdateRequest(BaseModel):
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    key_wins: Optional[list[str]] = None
    challenges: Optional[list[str]] = None
    work_highlights: Optional[str] = None
    training_summary: Optional[str] = None
    personal_wins: Optional[list[str]] = None
    health_metrics: Optional[dict] = None
    goal_progress: Optional[dict] = None
    focus_next: Optional[list[str]] = None


class ReviewOut(BaseModel):
    id: str
    period_start: str
    period_end: str
    key_wins: list[str]
    challenges: list[str]
    work_highlights: str
    training_summary: str
    personal_wins: list[str]
    health_metrics: Optional[dict]
    goal_progress: Optional[dict]
    focus_next: list[str]
    created_at: str
    updated_at: str


# --- Profile JSON helpers ---


def _load_profile() -> dict:
    """Load profile from JSON file."""
    if PROFILE_FILE.exists():
        try:
            with open(PROFILE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return LifeProfile().model_dump()


def _save_profile(data: dict) -> None:
    """Save profile to JSON file."""
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# --- Profile Endpoints ---


@router.get("")
def get_profile() -> dict:
    """Get full life profile."""
    return _load_profile()


@router.put("")
def update_profile(profile: LifeProfile) -> dict:
    """Update full life profile."""
    data = profile.model_dump()
    _save_profile(data)
    return data


@router.patch("/{section}")
def update_section(section: str, request_body: Any = Body(...)) -> dict:
    """Update a single profile section."""
    valid_sections = {"overview", "personal", "work", "training", "goals"}
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section: {section}. Must be one of: {', '.join(sorted(valid_sections))}",
        )

    profile = _load_profile()
    profile[section] = request_body
    _save_profile(profile)
    return profile


# --- Review Endpoints ---


def _row_to_review(row: tuple, columns: list[str]) -> dict:
    """Convert a DuckDB row to a review dict."""
    d = dict(zip(columns, row))
    # Convert date/timestamp objects to strings
    for key in ("period_start", "period_end"):
        if isinstance(d.get(key), date):
            d[key] = d[key].isoformat()
    for key in ("created_at", "updated_at"):
        if isinstance(d.get(key), datetime):
            d[key] = d[key].isoformat()
    # Ensure list fields are never None
    for key in ("key_wins", "challenges", "personal_wins", "focus_next"):
        if d.get(key) is None:
            d[key] = []
    # Ensure text fields are never None
    for key in ("work_highlights", "training_summary"):
        if d.get(key) is None:
            d[key] = ""
    return d


@router.get("/reviews")
def list_reviews(request: Request) -> list[dict]:
    """List all progress reviews, newest first."""
    db = request.app.state.db
    result = db.execute(
        "SELECT * FROM progress_reviews ORDER BY period_start DESC"
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()
    return [_row_to_review(row, columns) for row in rows]


@router.post("/reviews", status_code=201)
def create_review(review: ReviewCreateRequest, request: Request) -> dict:
    """Create a new progress review."""
    db = request.app.state.db
    review_id = str(uuid.uuid4())[:8]

    db.execute(
        """
        INSERT INTO progress_reviews (
            id, period_start, period_end, key_wins, challenges,
            work_highlights, training_summary, personal_wins,
            health_metrics, goal_progress, focus_next
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            review_id,
            review.period_start,
            review.period_end,
            review.key_wins,
            review.challenges,
            review.work_highlights,
            review.training_summary,
            review.personal_wins,
            json.dumps(review.health_metrics) if review.health_metrics else None,
            json.dumps(review.goal_progress) if review.goal_progress else None,
            review.focus_next,
        ],
    )

    # Fetch the created review
    result = db.execute(
        "SELECT * FROM progress_reviews WHERE id = ?", [review_id]
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_review(row, columns)


@router.get("/reviews/{review_id}")
def get_review(review_id: str, request: Request) -> dict:
    """Get a single progress review by ID."""
    db = request.app.state.db
    result = db.execute(
        "SELECT * FROM progress_reviews WHERE id = ?", [review_id]
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    return _row_to_review(row, columns)


@router.put("/reviews/{review_id}")
def update_review(
    review_id: str, review: ReviewUpdateRequest, request: Request
) -> dict:
    """Update an existing progress review."""
    db = request.app.state.db

    # Check exists
    existing = db.execute(
        "SELECT id FROM progress_reviews WHERE id = ?", [review_id]
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")

    # Build dynamic update
    updates = []
    params = []
    for field, value in review.model_dump(exclude_unset=True).items():
        if field in ("health_metrics", "goal_progress") and value is not None:
            updates.append(f"{field} = ?")
            params.append(json.dumps(value))
        else:
            updates.append(f"{field} = ?")
            params.append(value)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(review_id)
        db.execute(
            f"UPDATE progress_reviews SET {', '.join(updates)} WHERE id = ?",
            params,
        )

    # Fetch updated review
    result = db.execute(
        "SELECT * FROM progress_reviews WHERE id = ?", [review_id]
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()
    return _row_to_review(row, columns)


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: str, request: Request) -> None:
    """Delete a progress review."""
    db = request.app.state.db

    existing = db.execute(
        "SELECT id FROM progress_reviews WHERE id = ?", [review_id]
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")

    db.execute("DELETE FROM progress_reviews WHERE id = ?", [review_id])
