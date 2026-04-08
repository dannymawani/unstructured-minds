"""Auto-label exercises missing from exercise_definitions.json.

Scans the exercise_log for names not in the definitions file, calls Claude
to generate muscle groups / category / recovery hours, and merges back.

Usage:
    cd backend
    python3 -m scripts.auto_label_exercises              # dry-run (preview only)
    python3 -m scripts.auto_label_exercises --apply       # write to definitions file
    python3 -m scripts.auto_label_exercises --apply --db neon  # use Neon DB
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFINITIONS_PATH = REPO_ROOT / "shared" / "exercise_definitions.json"
LOCAL_DB_PATH = REPO_ROOT / "data" / "unstructured.duckdb"

# Activities / non-exercises that should be skipped, not labelled
SKIP_PATTERNS = {
    "cold plunge", "sauna", "walk", "swimming", "running", "trail run",
    "mobility work", "mobility", "sparring", "guard retention drilling",
    "gymnastic", "x-guard", "single leg x guard", "running and dancing",
    "walk with chris", "friday evening hangout with friends",
}


def load_definitions() -> dict:
    with open(DEFINITIONS_PATH) as f:
        return json.load(f)


def build_known_set(defs: dict) -> set[str]:
    """All known names (keys, display names, aliases) lowercased."""
    known: set[str] = set()
    for key, entry in defs.items():
        known.add(key.lower())
        known.add(entry["display"].lower())
        for alias in entry.get("aliases", []):
            known.add(alias.lower())
    return known


def get_db_exercises(use_neon: bool) -> list[str]:
    """Get all distinct exercise names from the database."""
    if use_neon:
        import psycopg2

        url = os.environ.get("DATABASE_URL")
        if not url:
            print("ERROR: DATABASE_URL not set for Neon mode")
            sys.exit(1)
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT exercise_name FROM exercise_log WHERE exercise_name IS NOT NULL ORDER BY exercise_name")
        rows = cur.fetchall()
        conn.close()
    else:
        import duckdb

        db = duckdb.connect(str(LOCAL_DB_PATH), read_only=True)
        rows = db.execute(
            "SELECT DISTINCT exercise_name FROM exercise_log WHERE exercise_name IS NOT NULL ORDER BY exercise_name"
        ).fetchall()
        db.close()

    return [r[0] for r in rows]


def find_unmapped(db_exercises: list[str], known: set[str]) -> list[str]:
    """Return exercises not in definitions and not in skip list."""
    unmapped = []
    for name in db_exercises:
        low = name.strip().lower()
        underscore = low.replace(" ", "_").replace("-", "_")
        if low in known or underscore in known:
            continue
        if low in SKIP_PATTERNS:
            continue
        # Skip generic "X exercises" entries
        if low.endswith(" exercises"):
            continue
        unmapped.append(name)
    return unmapped


async def classify_with_claude(unmapped: list[str], existing_defs: dict) -> dict:
    """Call Claude to generate full exercise definitions."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try loading from .env
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found")
        sys.exit(1)

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Show existing muscle groups for reference
    all_muscles = set()
    all_categories = set()
    for entry in existing_defs.values():
        all_muscles.update(entry.get("muscle_groups", []))
        all_categories.add(entry.get("category", ""))

    existing_names = [e["display"] for e in existing_defs.values()]

    tool = {
        "name": "label_exercises",
        "description": "Generate exercise definitions with muscle groups, category, and recovery hours",
        "input_schema": {
            "type": "object",
            "properties": {
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "Snake_case key for the exercise (e.g. 'ghd_crunch')",
                            },
                            "display": {
                                "type": "string",
                                "description": "Title Case display name (e.g. 'GHD Crunch')",
                            },
                            "aliases": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Alternative names this exercise might be logged as",
                            },
                            "muscle_groups": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Primary muscle groups worked",
                            },
                            "category": {
                                "type": "string",
                                "description": "Exercise category",
                            },
                            "recovery_hours": {
                                "type": "integer",
                                "description": "Typical recovery time in hours (24, 48, or 72)",
                            },
                            "is_exercise": {
                                "type": "boolean",
                                "description": "False if this is an activity/non-exercise that should be skipped",
                            },
                        },
                        "required": ["key", "display", "aliases", "muscle_groups", "category", "recovery_hours", "is_exercise"],
                    },
                },
            },
            "required": ["exercises"],
        },
    }

    exercise_list = "\n".join(f"- {name}" for name in unmapped)
    muscle_list = ", ".join(sorted(all_muscles))
    category_list = ", ".join(sorted(all_categories - {""}))

    prompt = f"""Classify these exercise names into full definitions. For each one, provide:
- A snake_case key
- A clean display name
- Any aliases (the raw name as logged, if different from display)
- Muscle groups (use existing group names where possible)
- Category
- Recovery hours (24 for isolation/light, 48 for compound, 72 for heavy compounds)
- Whether it's actually an exercise (set is_exercise=false for activities like walks, stretching, etc.)

If a name looks like it should map to an existing exercise (e.g. "Chinups" = pull-up variant), still create a NEW definition for it — we want every exercise to have its own entry.

Existing muscle groups: {muscle_list}
Existing categories: {category_list}
Existing exercises (for reference): {', '.join(existing_names)}

Names to classify:
{exercise_list}

Use the label_exercises tool to return your classifications."""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        tools=[tool],
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "label_exercises":
            return block.input

    return {"exercises": []}


def main():
    parser = argparse.ArgumentParser(description="Auto-label unmapped exercises")
    parser.add_argument("--apply", action="store_true", help="Write changes to exercise_definitions.json")
    parser.add_argument("--db", choices=["local", "neon"], default="local", help="Database to scan (default: local)")
    args = parser.parse_args()

    defs = load_definitions()
    known = build_known_set(defs)

    print(f"Loaded {len(defs)} exercise definitions")

    db_exercises = get_db_exercises(use_neon=args.db == "neon")
    print(f"Found {len(db_exercises)} unique exercises in DB")

    unmapped = find_unmapped(db_exercises, known)

    if not unmapped:
        print("All exercises are mapped!")
        return

    print(f"\n{len(unmapped)} unmapped exercises:")
    for name in unmapped:
        print(f"  - {name}")

    print("\nCalling Claude to classify...")
    result = asyncio.run(classify_with_claude(unmapped, defs))

    exercises = result.get("exercises", [])
    real_exercises = [e for e in exercises if e.get("is_exercise", True)]
    skipped = [e for e in exercises if not e.get("is_exercise", True)]

    if skipped:
        print(f"\nSkipped {len(skipped)} non-exercises:")
        for e in skipped:
            print(f"  - {e['display']}")

    if not real_exercises:
        print("No new exercises to add.")
        return

    print(f"\nNew definitions to add ({len(real_exercises)}):")
    for e in real_exercises:
        muscles = ", ".join(e["muscle_groups"])
        print(f"  {e['display']:35s} [{e['category']:12s}] {muscles}")

    if not args.apply:
        print("\nDry run — use --apply to write changes.")
        return

    # Merge into definitions
    for e in real_exercises:
        key = e["key"]
        if key in defs:
            print(f"  SKIP (key exists): {key}")
            continue
        defs[key] = {
            "display": e["display"],
            "aliases": e.get("aliases", []),
            "muscle_groups": e["muscle_groups"],
            "category": e["category"],
            "recovery_hours": e["recovery_hours"],
        }

    with open(DEFINITIONS_PATH, "w") as f:
        json.dump(defs, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nUpdated {DEFINITIONS_PATH}")


if __name__ == "__main__":
    main()
