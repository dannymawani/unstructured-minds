"""Demo data lifecycle: per-date cleanup, full clear, and graduation check."""

from typing import Any

from ..db.sql_compat import get_dialect, placeholder
from ..logging_config import get_logger
from .constants import DEMO_SOURCE_FILE, GRADUATION_THRESHOLD

logger = get_logger(__name__)

# Tables that have a date column and source_file column
_DATE_TABLES = ["activities", "exercise_log", "daily_metrics", "food_log", "tasks"]


def cleanup_demo_for_date(db, target_date: str, user_id: str) -> int:
    """Delete demo rows for a specific date across all tables.

    Called after a successful extraction to replace demo data for that date
    with real user data.

    Returns the total number of rows deleted.
    """
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    total = 0

    for table in _DATE_TABLES:
        conditions = [f"source_file = {ph}", f"date = {ph}"]
        params: list[Any] = [DEMO_SOURCE_FILE, target_date]
        if dialect == "postgres":
            conditions.append(f"user_id = {ph}")
            params.append(user_id)

        where = " AND ".join(conditions)

        # Count before delete (works on both DuckDB and Postgres)
        count = db.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", list(params)).fetchone()[0]
        if count > 0:
            db.execute(f"DELETE FROM {table} WHERE {where}", list(params))
            total += count

    if total > 0:
        logger.info("demo_cleanup_for_date", date=target_date, user_id=user_id, rows_deleted=total)
    return total


def clear_all_demo_data(db, user_id: str) -> int:
    """Delete ALL demo rows across all tables for this user.

    Returns total rows deleted.
    """
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    total = 0

    for table in _DATE_TABLES:
        conditions = [f"source_file = {ph}"]
        params: list[Any] = [DEMO_SOURCE_FILE]
        if dialect == "postgres":
            conditions.append(f"user_id = {ph}")
            params.append(user_id)

        where = " AND ".join(conditions)
        count = db.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", list(params)).fetchone()[0]
        if count > 0:
            db.execute(f"DELETE FROM {table} WHERE {where}", list(params))
            total += count

    logger.info("demo_data_cleared", user_id=user_id, rows_deleted=total)
    return total


def check_graduation(db, user_id: str) -> bool:
    """Check if user has enough real data to graduate from demo mode.

    Returns True if user has >= GRADUATION_THRESHOLD unique dates with real
    (non-demo) extraction data.
    """
    dialect = get_dialect(db)
    ph = placeholder(dialect)

    conditions = [f"source_file != {ph}"]
    params: list[Any] = [DEMO_SOURCE_FILE]
    if dialect == "postgres":
        conditions.append(f"user_id = {ph}")
        params.append(user_id)

    where = " AND ".join(conditions)
    result = db.execute(
        f"SELECT COUNT(DISTINCT date) FROM daily_metrics WHERE {where}",
        params,
    ).fetchone()

    real_dates = result[0] if result else 0
    return real_dates >= GRADUATION_THRESHOLD


def get_demo_data_count(db, user_id: str) -> int:
    """Count total demo rows across all tables for this user."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    total = 0

    for table in _DATE_TABLES:
        conditions = [f"source_file = {ph}"]
        params: list[Any] = [DEMO_SOURCE_FILE]
        if dialect == "postgres":
            conditions.append(f"user_id = {ph}")
            params.append(user_id)

        result = db.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {' AND '.join(conditions)}",
            params,
        ).fetchone()
        total += result[0] if result else 0

    return total


def get_real_data_count(db, user_id: str) -> int:
    """Count total real (non-demo) rows across core tables for this user."""
    dialect = get_dialect(db)
    ph = placeholder(dialect)
    total = 0

    for table in _DATE_TABLES:
        conditions = [f"source_file != {ph}"]
        params: list[Any] = [DEMO_SOURCE_FILE]
        if dialect == "postgres":
            conditions.append(f"user_id = {ph}")
            params.append(user_id)

        result = db.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {' AND '.join(conditions)}",
            params,
        ).fetchone()
        total += result[0] if result else 0

    return total
