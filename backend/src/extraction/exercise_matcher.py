"""Fuzzy exercise name matching against exercise_definitions.json."""

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


class ExerciseMatcher:
    """Normalizes exercise names using a 3-tier matching strategy.

    1. Exact match — case-insensitive against keys and display names
    2. Alias match — case-insensitive against all aliases
    3. Fuzzy match — difflib.SequenceMatcher with threshold >= 0.75

    The canonical name returned is the `display` value from exercise_definitions.
    """

    FUZZY_THRESHOLD = 0.75

    def __init__(self, definitions_path: Path) -> None:
        self._exact_map: dict[str, str] = {}
        self._alias_map: dict[str, str] = {}
        self._fuzzy_candidates: list[tuple[str, str]] = []  # (lowercase_name, display)

        if not definitions_path.exists():
            return

        with open(definitions_path) as f:
            definitions: dict[str, Any] = json.load(f)

        for key, entry in definitions.items():
            display = entry["display"]

            # Exact: key and display name (lowercased)
            self._exact_map[key.lower()] = display
            self._exact_map[display.lower()] = display

            # Fuzzy candidates: display name + all aliases
            self._fuzzy_candidates.append((display.lower(), display))

            # Aliases
            for alias in entry.get("aliases", []):
                self._alias_map[alias.lower()] = display
                self._fuzzy_candidates.append((alias.lower(), display))

    def match(self, raw_name: str) -> tuple[str, float]:
        """Match a raw exercise name to a canonical name.

        Returns:
            (canonical_name, confidence) where confidence is 1.0 for
            exact/alias matches, 0.0-1.0 for fuzzy, and 0.0 if no match.
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

        # 3. Fuzzy match against display names and aliases
        best_score = 0.0
        best_match = raw_name

        for candidate_lower, display in self._fuzzy_candidates:
            score = SequenceMatcher(None, normalized, candidate_lower).ratio()
            if score > best_score:
                best_score = score
                best_match = display

        if best_score >= self.FUZZY_THRESHOLD:
            return (best_match, round(best_score, 3))

        # No match — return original name unchanged
        return (raw_name, 0.0)
