"""Fuzzy exercise name matching against exercise_definitions.json."""

import json
import tempfile
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


class ExerciseMatcher:
    """Normalizes exercise names using a multi-tier matching strategy.

    1. Exact match — case-insensitive against keys and display names
    2. Alias match — case-insensitive against all aliases
    3. AI cache  — previously classified names (confidence 0.95)
    4. Fuzzy match — difflib.SequenceMatcher with threshold >= 0.75
    5. Title-case fallback — return raw_name.strip().title() to avoid case dupes

    The canonical name returned is the `display` value from exercise_definitions.
    """

    FUZZY_THRESHOLD = 0.75
    AI_CACHE_CONFIDENCE = 0.95

    def __init__(self, definitions_path: Path) -> None:
        self._exact_map: dict[str, str] = {}
        self._alias_map: dict[str, str] = {}
        self._fuzzy_candidates: list[tuple[str, str]] = []  # (lowercase_name, display)
        self._ai_cache: dict[str, str] = {}  # lowercased raw → canonical
        self._canonical_set: set[str] = set()  # all known display names
        self._muscle_groups: dict[str, list[str]] = {}  # display_name → muscle_groups
        self._categories: dict[str, str] = {}  # display_name → category
        self._recovery_hours: dict[str, int] = {}  # display_name → recovery_hours

        if not definitions_path.exists():
            return

        with open(definitions_path) as f:
            definitions: dict[str, Any] = json.load(f)

        for key, entry in definitions.items():
            display = entry["display"]
            self._canonical_set.add(display)

            # Exact: key and display name (lowercased)
            self._exact_map[key.lower()] = display
            self._exact_map[display.lower()] = display

            # Fuzzy candidates: display name + all aliases
            self._fuzzy_candidates.append((display.lower(), display))

            # Aliases
            for alias in entry.get("aliases", []):
                self._alias_map[alias.lower()] = display
                self._fuzzy_candidates.append((alias.lower(), display))

            # Metadata
            self._muscle_groups[display] = entry.get("muscle_groups", [])
            self._categories[display] = entry.get("category", "other")
            self._recovery_hours[display] = entry.get("recovery_hours", 48)

    @property
    def canonical_names(self) -> list[str]:
        """Return sorted list of all known canonical display names."""
        return sorted(self._canonical_set)

    def get_muscle_groups(self, canonical_name: str) -> list[str]:
        """Look up muscle groups for a canonical exercise name.

        Checks both builtin definitions and community exercises.
        """
        if canonical_name in self._muscle_groups:
            return self._muscle_groups[canonical_name]
        return []

    def get_metadata(self, canonical_name: str) -> dict[str, Any]:
        """Get full metadata for a canonical exercise name.

        Returns dict with muscle_groups, category, recovery_hours.
        """
        return {
            "muscle_groups": self._muscle_groups.get(canonical_name, []),
            "category": self._categories.get(canonical_name, "other"),
            "recovery_hours": self._recovery_hours.get(canonical_name, 48),
        }

    def load_community_exercises(self, exercises: list[dict]) -> None:
        """Inject community exercises into the matcher's lookup maps.

        Community exercises are loaded from the database and treated
        the same as built-in definitions for matching purposes.

        Args:
            exercises: List of dicts with keys: exercise_key, display_name,
                       aliases (list or JSON string), muscle_groups, category,
                       recovery_hours.
        """
        count = 0
        for entry in exercises:
            key = entry["exercise_key"]
            display = entry["display_name"]

            # Skip if already registered (builtins take precedence)
            if display in self._canonical_set:
                continue

            self._canonical_set.add(display)
            self._exact_map[key.lower()] = display
            self._exact_map[display.lower()] = display
            self._fuzzy_candidates.append((display.lower(), display))

            # Parse aliases — may be a JSON string (DuckDB) or list (Postgres)
            aliases = entry.get("aliases", [])
            if isinstance(aliases, str):
                try:
                    aliases = json.loads(aliases)
                except (json.JSONDecodeError, TypeError):
                    aliases = []

            for alias in aliases:
                self._alias_map[alias.lower()] = display
                self._fuzzy_candidates.append((alias.lower(), display))

            # Store metadata
            muscle_groups = entry.get("muscle_groups", [])
            if isinstance(muscle_groups, str):
                try:
                    muscle_groups = json.loads(muscle_groups)
                except (json.JSONDecodeError, TypeError):
                    muscle_groups = []
            self._muscle_groups[display] = muscle_groups or []
            self._categories[display] = entry.get("category", "other")
            self._recovery_hours[display] = entry.get("recovery_hours", 48)

            count += 1

        if count:
            logger.info("community_exercises_loaded", count=count)

    def suggest(self, query: str, limit: int = 10) -> list[dict]:
        """Suggest exercises matching a query string.

        Uses prefix matching first, then fuzzy matching as fallback.

        Args:
            query: Partial exercise name to match
            limit: Maximum number of results

        Returns:
            List of dicts with name, source ("builtin"/"community" not tracked
            at this level — caller annotates source).
        """
        if not query:
            return []

        q = query.strip().lower()
        results: list[tuple[str, float]] = []
        seen: set[str] = set()

        # Prefix matches (highest priority)
        for candidate_lower, display in self._fuzzy_candidates:
            if display in seen:
                continue
            if candidate_lower.startswith(q) or q in candidate_lower:
                results.append((display, 1.0))
                seen.add(display)

        # Fuzzy matches for remaining
        if len(results) < limit:
            for candidate_lower, display in self._fuzzy_candidates:
                if display in seen:
                    continue
                score = SequenceMatcher(None, q, candidate_lower).ratio()
                if score >= 0.5:
                    results.append((display, score))
                    seen.add(display)

        # Sort by score descending, take top N
        results.sort(key=lambda x: x[1], reverse=True)
        return [{"name": name} for name, _ in results[:limit]]

    def load_ai_cache(self, path: Path) -> None:
        """Load AI classification cache from disk.

        Args:
            path: Path to ai_exercise_cache.json
        """
        if not path.exists():
            return
        try:
            with open(path) as f:
                data = json.load(f)
            self._ai_cache = {k.lower(): v for k, v in data.items()}
            logger.info("ai_cache_loaded", count=len(self._ai_cache), path=str(path))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("ai_cache_load_failed", error=str(e))

    def update_ai_cache(self, mappings: dict[str, str], path: Path) -> None:
        """Merge new AI mappings into cache and write atomically.

        Args:
            mappings: dict of raw_name → canonical_name
            path: Path to ai_exercise_cache.json
        """
        # Merge into in-memory cache (lowercased keys)
        for raw, canonical in mappings.items():
            self._ai_cache[raw.lower()] = canonical

        # Write atomically via temp file
        cache_to_write = {k: v for k, v in self._ai_cache.items()}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", dir=str(path.parent), suffix=".tmp", delete=False
            ) as tmp:
                json.dump(cache_to_write, tmp, indent=2, ensure_ascii=False)
                tmp_path = Path(tmp.name)
            tmp_path.rename(path)
            logger.info("ai_cache_updated", count=len(cache_to_write), path=str(path))
        except OSError as e:
            logger.warning("ai_cache_write_failed", error=str(e))

    def load_ai_cache_from_settings(self, settings_store) -> None:
        """Load AI classification cache from Postgres user_settings.

        Args:
            settings_store: UserSettingsStore instance
        """
        try:
            data = settings_store.get("ai_exercise_cache")
            if data:
                self._ai_cache = {k.lower(): v for k, v in data.items()}
                logger.info("ai_cache_loaded", count=len(self._ai_cache), source="postgres")
        except Exception as e:
            logger.warning("ai_cache_load_from_settings_failed", error=str(e))

    def update_ai_cache_to_settings(self, mappings: dict[str, str], settings_store) -> None:
        """Merge new AI mappings into cache and write to Postgres user_settings.

        Args:
            mappings: dict of raw_name → canonical_name
            settings_store: UserSettingsStore instance
        """
        for raw, canonical in mappings.items():
            self._ai_cache[raw.lower()] = canonical

        cache_to_write = {k: v for k, v in self._ai_cache.items()}
        try:
            settings_store.set("ai_exercise_cache", cache_to_write)
            logger.info("ai_cache_updated", count=len(cache_to_write), source="postgres")
        except Exception as e:
            logger.warning("ai_cache_write_to_settings_failed", error=str(e))

    def match(self, raw_name: str) -> tuple[str, float]:
        """Match a raw exercise name to a canonical name.

        Returns:
            (canonical_name, confidence) where confidence is 1.0 for
            exact/alias matches, 0.95 for AI cache, 0.0-1.0 for fuzzy,
            and 0.0 if no match (title-cased fallback).
        """
        if not raw_name:
            return (raw_name, 0.0)

        normalized = raw_name.strip().lower()

        # 1. Exact match on key or display name
        if normalized in self._exact_map:
            return (self._exact_map[normalized], 1.0)

        # Also try underscore variant (e.g. "bench press" -> "bench_press")
        underscore_variant = normalized.replace(" ", "_")
        if underscore_variant in self._exact_map:
            return (self._exact_map[underscore_variant], 1.0)

        # 2. Alias match
        if normalized in self._alias_map:
            return (self._alias_map[normalized], 1.0)

        # 3. AI cache match
        if normalized in self._ai_cache:
            return (self._ai_cache[normalized], self.AI_CACHE_CONFIDENCE)

        # 4. Fuzzy match against display names and aliases
        best_score = 0.0
        best_match = raw_name

        for candidate_lower, display in self._fuzzy_candidates:
            score = SequenceMatcher(None, normalized, candidate_lower).ratio()
            if score > best_score:
                best_score = score
                best_match = display

        if best_score >= self.FUZZY_THRESHOLD:
            return (best_match, round(best_score, 3))

        # 5. Title-case fallback — prevents case-only duplicates
        return (raw_name.strip().title(), 0.0)
