#!/usr/bin/env python3
"""Validate migration output against source data."""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data"


def test_exercise_log():
    path = DATA / "exercise_log.csv"
    assert path.exists(), "exercise_log.csv not found"

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        rows = list(reader)

    # Column renames applied
    assert "exercise_name" in headers, "exercise_name column missing"
    assert "set_number" in headers, "set_number column missing"
    assert "duration_minutes" in headers, "duration_minutes column missing"
    assert "exercise" not in headers, "old 'exercise' column should not exist"
    assert "sets" not in headers, "old 'sets' column should not exist"
    assert "duration_min" not in headers, "old 'duration_min' column should not exist"

    # All rows have dates
    for row in rows:
        assert row["date"], f"Empty date in row: {row}"

    # Sorted by date
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates), "Rows not sorted by date"

    # No duplicate primary keys
    keys = set()
    for row in rows:
        key = (row["date"], row["activity_id"], row["exercise_name"], row["set_number"])
        assert key not in keys, f"Duplicate key: {key}"
        keys.add(key)

    print(f"exercise_log: {len(rows)} rows, {len(headers)} columns - OK")


def test_food_log():
    path = DATA / "food_log.csv"
    assert path.exists(), "food_log.csv not found"

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    dates = [r["date"] for r in rows]
    assert dates == sorted(dates), "Rows not sorted by date"
    print(f"food_log: {len(rows)} rows - OK")


def test_daily_metrics():
    path = DATA / "daily_metrics.csv"
    assert path.exists(), "daily_metrics.csv not found"

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    dates = [r["date"] for r in rows]
    assert dates == sorted(dates), "Rows not sorted by date"
    assert len(dates) == len(set(dates)), "Duplicate dates in daily_metrics"
    print(f"daily_metrics: {len(rows)} rows - OK")


def test_daily_tasks():
    path = DATA / "daily_tasks.csv"
    assert path.exists(), "daily_tasks.csv not found"

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    dates = [r["date"] for r in rows]
    assert dates == sorted(dates), "Rows not sorted by date"
    print(f"daily_tasks: {len(rows)} rows - OK")


def test_config_files():
    for name in ["exercise_definitions.json", "training_config.json", "injury_config.json"]:
        path = DATA / name
        assert path.exists(), f"{name} not found"
    print("Config files: all 3 present - OK")


def test_schemas():
    schema_dir = DATA / "schemas"
    assert schema_dir.exists(), "schemas directory not found"
    expected = ["exercise_log.json", "food_log.json", "daily_metrics.json", "daily_tasks.json"]
    for name in expected:
        assert (schema_dir / name).exists(), f"Schema {name} not found"
    print(f"Schemas: {len(list(schema_dir.glob('*.json')))} files - OK")


if __name__ == "__main__":
    test_exercise_log()
    test_food_log()
    test_daily_metrics()
    test_daily_tasks()
    test_config_files()
    test_schemas()
    print("\nAll validation checks passed!")
