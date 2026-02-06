#!/usr/bin/env python3
"""Migrate existing date-partitioned CSV data to flat files for DuckDB.

Scans existing_data/data/{type}/{year}/{month}/{day}/ directories,
concatenates CSVs into single flat files per data type, transforms
column names for exercise_log, copies config files and schemas.

Usage:
    python scripts/migrate_existing_data.py [--dry-run]
"""

import csv
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXISTING_DATA = PROJECT_ROOT / "existing_data" / "data"
TARGET_DATA = PROJECT_ROOT / "data"

DATA_TYPES = ["exercise_log", "food_log", "daily_metrics", "daily_tasks"]

CONFIG_FILES = [
    "exercise_definitions.json",
    "training_config.json",
    "injury_config.json",
]

# Column renames for exercise_log
EXERCISE_LOG_RENAMES = {
    "exercise": "exercise_name",
    "duration_min": "duration_minutes",
}


def find_csv_files(data_type: str) -> list[Path]:
    """Find all CSV files for a data type in the date-partitioned structure."""
    type_dir = EXISTING_DATA / data_type
    if not type_dir.exists():
        return []
    csv_files = sorted(type_dir.rglob("*.csv"))
    return csv_files


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    """Read a CSV file and return headers and rows."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def transform_exercise_log(headers: list[str], rows: list[dict]) -> tuple[list[str], list[dict]]:
    """Transform exercise_log columns and compute set_number."""
    # Rename columns
    new_headers = []
    for h in headers:
        new_headers.append(EXERCISE_LOG_RENAMES.get(h, h))

    # Rename 'sets' to 'set_number' if present, but the existing data
    # already has one row per set. We compute set_number sequentially.
    if "sets" in new_headers:
        idx = new_headers.index("sets")
        new_headers[idx] = "set_number"

    # If set_number not in headers, add it
    if "set_number" not in new_headers:
        new_headers.insert(new_headers.index("exercise_name") + 1 if "exercise_name" in new_headers else len(new_headers), "set_number")

    transformed = []
    # Track set numbers per (activity_id, exercise_name) group
    set_counters: dict[tuple[str, str], int] = defaultdict(int)

    for row in rows:
        new_row = {}
        for old_key, value in row.items():
            new_key = EXERCISE_LOG_RENAMES.get(old_key, old_key)
            if old_key == "sets":
                continue  # We'll compute set_number instead
            new_row[new_key] = value

        activity_id = new_row.get("activity_id", "")
        exercise_name = new_row.get("exercise_name", "")
        key = (activity_id, exercise_name)
        set_counters[key] += 1
        new_row["set_number"] = str(set_counters[key])

        transformed.append(new_row)

    return new_headers, transformed


def deduplicate(rows: list[dict], data_type: str) -> list[dict]:
    """Remove duplicate rows based on primary key for each data type."""
    if data_type == "exercise_log":
        seen = set()
        unique = []
        for row in rows:
            key = (
                row.get("date", ""),
                row.get("activity_id", ""),
                row.get("exercise_name", ""),
                row.get("set_number", ""),
            )
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique
    elif data_type == "daily_tasks":
        seen = set()
        unique = []
        for row in rows:
            key = (row.get("task_id", ""), row.get("date", ""))
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique
    elif data_type == "daily_metrics":
        seen = set()
        unique = []
        for row in rows:
            key = row.get("date", "")
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique
    elif data_type == "food_log":
        seen = set()
        unique = []
        for row in rows:
            key = (
                row.get("date", ""),
                row.get("meal", ""),
                row.get("food", ""),
            )
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique
    return rows


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    """Write rows to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def copy_configs(dry_run: bool = False) -> list[str]:
    """Copy config files to target data directory."""
    copied = []
    for config_file in CONFIG_FILES:
        src = EXISTING_DATA / config_file
        dst = TARGET_DATA / config_file
        if src.exists():
            if not dry_run:
                shutil.copy2(src, dst)
            copied.append(config_file)
    return copied


def copy_schemas(dry_run: bool = False) -> list[str]:
    """Copy and update schema files."""
    copied = []
    src_dir = EXISTING_DATA / "schemas"
    dst_dir = TARGET_DATA / "schemas"

    if not src_dir.exists():
        return copied

    for schema_file in sorted(src_dir.glob("*.json")):
        if not dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)

            # For exercise_log schema, update column names
            if schema_file.name == "exercise_log.json":
                with open(schema_file, encoding="utf-8") as f:
                    schema = json.load(f)

                for col in schema.get("columns", []):
                    if col["name"] in EXERCISE_LOG_RENAMES:
                        col["name"] = EXERCISE_LOG_RENAMES[col["name"]]
                    if col["name"] == "sets":
                        col["name"] = "set_number"
                        col["description"] = "Sequential set number per exercise per activity"

                with open(dst_dir / schema_file.name, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2)
                    f.write("\n")
            else:
                shutil.copy2(schema_file, dst_dir / schema_file.name)

        copied.append(schema_file.name)

    return copied


def migrate(dry_run: bool = False) -> None:
    """Run the full migration."""
    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating data from {EXISTING_DATA}")
    print(f"Target: {TARGET_DATA}")
    print()

    if not EXISTING_DATA.exists():
        print(f"ERROR: Source directory not found: {EXISTING_DATA}")
        sys.exit(1)

    if not dry_run:
        TARGET_DATA.mkdir(parents=True, exist_ok=True)

    total_source_rows = 0
    total_target_rows = 0

    for data_type in DATA_TYPES:
        csv_files = find_csv_files(data_type)
        if not csv_files:
            print(f"  {data_type}: No CSV files found, skipping")
            continue

        all_headers = []
        all_rows = []
        source_row_count = 0

        for csv_file in csv_files:
            headers, rows = read_csv(csv_file)
            if not all_headers and headers:
                all_headers = headers
            all_rows.extend(rows)
            source_row_count += len(rows)

        if not all_rows:
            print(f"  {data_type}: {len(csv_files)} files, 0 rows — skipping")
            continue

        # Transform exercise_log columns
        if data_type == "exercise_log":
            all_headers, all_rows = transform_exercise_log(all_headers, all_rows)

        # Deduplicate
        all_rows = deduplicate(all_rows, data_type)

        # Sort by date
        all_rows.sort(key=lambda r: r.get("date", ""))

        target_row_count = len(all_rows)
        dupes = source_row_count - target_row_count

        total_source_rows += source_row_count
        total_target_rows += target_row_count

        # Write
        if not dry_run:
            output_path = TARGET_DATA / f"{data_type}.csv"
            write_csv(output_path, all_headers, all_rows)

        print(
            f"  {data_type}: {len(csv_files)} files -> {target_row_count} rows"
            f"{f' ({dupes} duplicates removed)' if dupes else ''}"
        )

    print()

    # Copy config files
    configs = copy_configs(dry_run)
    print(f"Config files copied: {', '.join(configs) if configs else 'none'}")

    # Copy and update schemas
    schemas = copy_schemas(dry_run)
    print(f"Schema files copied: {', '.join(schemas) if schemas else 'none'}")

    print()
    print(f"Total: {total_source_rows} source rows -> {total_target_rows} target rows")
    print("Migration complete!" if not dry_run else "Dry run complete (no files written)")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    migrate(dry_run=dry_run)
