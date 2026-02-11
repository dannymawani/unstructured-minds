"""Exercise normalization orchestration.

Queries all exercise names from DuckDB, matches each via ExerciseMatcher,
collects unmatched names, and calls Claude for AI classification.
Results are cached to disk (or Postgres user_settings in hybrid mode)
so the AI call only happens once per new name.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..claude import ClaudeClient
from ..db import DatabaseManager
from ..logging_config import get_logger
from .exercise_matcher import ExerciseMatcher

logger = get_logger(__name__)


@dataclass
class NormalizationStats:
    """Stats from a normalization run."""

    total_names: int = 0
    already_matched: int = 0
    ai_classified: int = 0
    title_cased: int = 0
    errors: list[str] | None = None


async def normalize_exercises(
    db: DatabaseManager,
    matcher: ExerciseMatcher,
    claude: Optional[ClaudeClient],
    cache_path: Path,
    user_settings_store=None,
) -> NormalizationStats:
    """Normalize all exercise names in the database.

    1. Load existing AI cache
    2. Query all distinct exercise names from DB
    3. Match each through ExerciseMatcher
    4. Collect names that got no match (confidence 0.0)
    5. Call Claude to classify unmatched names
    6. Save AI cache

    Works gracefully without Claude — unmatched names get title-case fallback.

    Args:
        db: Database manager
        matcher: ExerciseMatcher instance (already loaded with definitions)
        claude: Claude client (optional — skips AI if None/unconfigured)
        cache_path: Path to ai_exercise_cache.json (used in duckdb mode)
        user_settings_store: Optional UserSettingsStore for cloud mode

    Returns:
        NormalizationStats with counts
    """
    stats = NormalizationStats(errors=[])

    # 1. Load existing AI cache (from Postgres or file)
    if user_settings_store:
        matcher.load_ai_cache_from_settings(user_settings_store)
    else:
        matcher.load_ai_cache(cache_path)

    # 2. Query all distinct exercise names
    try:
        rows = db.execute(
            "SELECT DISTINCT exercise_name FROM exercise_log WHERE exercise_name IS NOT NULL"
        ).fetchall()
    except Exception as e:
        logger.warning("normalize_db_query_failed", error=str(e))
        stats.errors.append(f"DB query failed: {e}")
        return stats

    all_names = [row[0] for row in rows]
    stats.total_names = len(all_names)

    if not all_names:
        logger.info("exercise_normalization_complete", **stats.__dict__)
        return stats

    # 3. Match each name and collect unmatched
    unmatched: list[str] = []
    for name in all_names:
        _, confidence = matcher.match(name)
        if confidence > 0.0:
            stats.already_matched += 1
        else:
            unmatched.append(name)

    # 4. Call Claude for unmatched names (if available)
    if unmatched and claude and claude.is_configured:
        try:
            ai_mappings = await claude.classify_exercises(
                unmatched_names=unmatched,
                known_canonical_names=matcher.canonical_names,
            )
            if ai_mappings:
                if user_settings_store:
                    matcher.update_ai_cache_to_settings(ai_mappings, user_settings_store)
                else:
                    matcher.update_ai_cache(ai_mappings, cache_path)
                stats.ai_classified = len(ai_mappings)
                logger.info(
                    "ai_exercise_classification_done",
                    classified=len(ai_mappings),
                    names=list(ai_mappings.keys()),
                )
        except Exception as e:
            logger.warning("ai_classification_failed", error=str(e))
            stats.errors.append(f"AI classification failed: {e}")

    # Count remaining unmatched (title-cased fallback)
    stats.title_cased = len(unmatched) - stats.ai_classified

    logger.info("exercise_normalization_complete", **stats.__dict__)
    return stats
