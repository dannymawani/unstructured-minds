#!/usr/bin/env python3
"""Normalize exercise names in the database to canonical forms.

Usage:
    cd backend
    python3 -m scripts.normalize_exercise_names --mode duckdb
    python3 -m scripts.normalize_exercise_names --mode postgres --user-id <UUID>
    python3 -m scripts.normalize_exercise_names --mode duckdb --dry-run
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import settings
from src.extraction.exercise_matcher import ExerciseMatcher


def main():
    parser = argparse.ArgumentParser(description="Normalize exercise names in the database")
    parser.add_argument("--mode", choices=["duckdb", "postgres"], default="duckdb")
    parser.add_argument("--user-id", help="User UUID (required for postgres)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    if args.mode == "postgres" and not args.user_id:
        parser.error("--user-id is required for postgres mode")

    # Set up DB connection
    if args.mode == "postgres":
        from src.db.postgres import PostgresManager
        db = PostgresManager(settings.database_url)
        db.connect()
        ph = "%s"
    else:
        from src.db.connection import DatabaseManager
        db = DatabaseManager(settings.data_path / "unstructured.duckdb")
        ph = "?"

    # Set up matcher — find exercise_definitions.json
    candidates = [
        Path("/app/shared/exercise_definitions.json"),  # Docker
        Path("shared/exercise_definitions.json"),  # cwd = project root
        Path(__file__).resolve().parent.parent.parent / "shared" / "exercise_definitions.json",
    ]
    defs_path = next((c for c in candidates if c.exists()), Path("shared/exercise_definitions.json"))
    matcher = ExerciseMatcher(defs_path)
    matcher.load_ai_cache(settings.data_path / "ai_exercise_cache.json")

    # Query distinct exercise names
    if args.mode == "postgres" and args.user_id:
        rows = db.execute(
            f"SELECT DISTINCT exercise_name FROM exercise_log WHERE user_id = {ph}",
            [args.user_id],
        ).fetchall()
    else:
        rows = db.execute("SELECT DISTINCT exercise_name FROM exercise_log").fetchall()

    all_names = [r[0] for r in rows if r[0]]
    print(f"Found {len(all_names)} distinct exercise names")

    # Build update map
    update_map: dict[str, str] = {}
    skipped = 0
    for name in all_names:
        canonical, confidence = matcher.match(name)
        if canonical != name and confidence > 0:
            update_map[name] = canonical
        else:
            skipped += 1

    print(f"  Already canonical: {skipped}")
    print(f"  To update: {len(update_map)}")

    if update_map:
        print("\nChanges:")
        for old, new in sorted(update_map.items()):
            print(f"  {old!r:40s} -> {new!r}")

    if args.dry_run or not update_map:
        if args.dry_run:
            print("\n(dry run — no changes written)")
        return

    # Apply updates
    updated = 0
    for old_name, canonical in update_map.items():
        if args.mode == "postgres" and args.user_id:
            db.execute(
                f"UPDATE exercise_log SET exercise_name = {ph} WHERE exercise_name = {ph} AND user_id = {ph}",
                [canonical, old_name, args.user_id],
            )
        else:
            db.execute(
                f"UPDATE exercise_log SET exercise_name = {ph} WHERE exercise_name = {ph}",
                [canonical, old_name],
            )
        updated += 1

    print(f"\nUpdated {updated} exercise name mappings")
    db.close()


if __name__ == "__main__":
    main()
