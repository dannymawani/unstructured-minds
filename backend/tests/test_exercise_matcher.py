"""Tests for ExerciseMatcher fuzzy matching."""

import json
from pathlib import Path

import pytest

from src.extraction.exercise_matcher import ExerciseMatcher


@pytest.fixture
def definitions_path(tmp_path: Path) -> Path:
    """Create a temporary exercise_definitions.json."""
    defs = {
        "deadlift": {
            "display": "Deadlift",
            "aliases": ["dødløft", "dødløft (deadlift)"],
            "muscle_groups": ["back", "hamstrings"],
            "category": "compound",
            "recovery_hours": 72,
        },
        "bench_press": {
            "display": "Bench Press",
            "aliases": [],
            "muscle_groups": ["chest"],
            "category": "compound",
            "recovery_hours": 48,
        },
        "military_press": {
            "display": "Military Press",
            "aliases": ["shoulder press"],
            "muscle_groups": ["shoulders"],
            "category": "compound",
            "recovery_hours": 48,
        },
        "leg_curl": {
            "display": "Leg Curl",
            "aliases": [],
            "muscle_groups": ["hamstrings"],
            "category": "legs",
            "recovery_hours": 48,
        },
        "squat": {
            "display": "Squat",
            "aliases": [],
            "muscle_groups": ["quads"],
            "category": "compound",
            "recovery_hours": 72,
        },
        "incline_dumbbell_press": {
            "display": "Incline Dumbbell Press",
            "aliases": ["skrå dumbbell press"],
            "muscle_groups": ["chest"],
            "category": "chest",
            "recovery_hours": 48,
        },
    }
    path = tmp_path / "exercise_definitions.json"
    path.write_text(json.dumps(defs))
    return path


@pytest.fixture
def matcher(definitions_path: Path) -> ExerciseMatcher:
    """Create an ExerciseMatcher with test definitions."""
    return ExerciseMatcher(definitions_path)


class TestExactMatch:
    """Exact match tests (confidence = 1.0)."""

    def test_display_name_exact(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("Deadlift")
        assert name == "Deadlift"
        assert conf == 1.0

    def test_case_insensitive(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("BENCH PRESS")
        assert name == "Bench Press"
        assert conf == 1.0

    def test_lowercase(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("deadlift")
        assert name == "Deadlift"
        assert conf == 1.0

    def test_key_match(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("bench_press")
        assert name == "Bench Press"
        assert conf == 1.0

    def test_space_to_underscore(self, matcher: ExerciseMatcher):
        """'bench press' should match key 'bench_press'."""
        name, conf = matcher.match("bench press")
        assert name == "Bench Press"
        assert conf == 1.0

    def test_whitespace_stripped(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("  Squat  ")
        assert name == "Squat"
        assert conf == 1.0


class TestAliasMatch:
    """Alias match tests (confidence = 1.0)."""

    def test_danish_alias(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("dødløft")
        assert name == "Deadlift"
        assert conf == 1.0

    def test_alias_case_insensitive(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("Shoulder Press")
        assert name == "Military Press"
        assert conf == 1.0

    def test_danish_alias_with_parens(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("dødløft (deadlift)")
        assert name == "Deadlift"
        assert conf == 1.0

    def test_danish_incline_alias(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("skrå dumbbell press")
        assert name == "Incline Dumbbell Press"
        assert conf == 1.0


class TestFuzzyMatch:
    """Fuzzy match tests (confidence between threshold and 1.0)."""

    def test_typo(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("bench pres")
        assert name == "Bench Press"
        assert 0.75 <= conf < 1.0

    def test_partial_name(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("deadlif")
        assert name == "Deadlift"
        assert 0.75 <= conf < 1.0

    def test_minor_misspelling(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("leg curls")
        assert name == "Leg Curl"
        assert 0.75 <= conf < 1.0


class TestNoMatch:
    """Tests for unrecognized exercises that pass through unchanged."""

    def test_extra_word_below_threshold(self, matcher: ExerciseMatcher):
        """Extra words drop the ratio below threshold — passes through."""
        name, conf = matcher.match("leg curl machine")
        assert name == "leg curl machine"
        assert conf == 0.0

    def test_unknown_exercise(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("underwater basket weaving")
        assert name == "underwater basket weaving"
        assert conf == 0.0

    def test_empty_string(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("")
        assert name == ""
        assert conf == 0.0

    def test_gibberish(self, matcher: ExerciseMatcher):
        name, conf = matcher.match("xyzzy plugh")
        assert name == "xyzzy plugh"
        assert conf == 0.0


class TestMissingDefinitions:
    """Tests when definitions file doesn't exist."""

    def test_missing_file_returns_original(self, tmp_path: Path):
        matcher = ExerciseMatcher(tmp_path / "nonexistent.json")
        name, conf = matcher.match("Deadlift")
        assert name == "Deadlift"
        assert conf == 0.0
