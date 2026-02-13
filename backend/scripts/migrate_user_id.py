"""Migrate Postgres rows from default_user_id to an authenticated user's uuid5.

Usage:
    cd backend
    python3 -m scripts.migrate_user_id --clerk-id "user_39XgYzwinap2GxAmggtHgU0ACa9"

This updates every table's user_id column from the hardcoded default UUID
to the deterministic uuid5-mapped UUID for the given Clerk sub.
"""

import argparse
import uuid

# Same namespace used in dependencies.py
CLERK_NAMESPACE = uuid.UUID("6ba7b811-6ba5-11d1-80b6-00c04fd430c8")

# All tables that have a user_id column in Postgres
TABLES_WITH_USER_ID = [
    "activities",
    "exercise_log",
    "daily_metrics",
    "food_log",
    "tasks",
    "extraction_log",
    "kanban_tasks",
    "kanban_task_updates",
    "progress_reviews",
    "vault_files",
    "user_settings",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate user_id from default to Clerk-mapped uuid5")
    parser.add_argument(
        "--clerk-id",
        required=True,
        help="Clerk user ID (sub claim), e.g. user_39XgYzwinap2GxAmggtHgU0ACa9",
    )
    parser.add_argument(
        "--old-user-id",
        default="00000000-0000-0000-0000-000000000001",
        help="Current user_id in the database (default: 00000000-0000-0000-0000-000000000001)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    args = parser.parse_args()

    new_user_id = str(uuid.uuid5(CLERK_NAMESPACE, args.clerk_id))
    print(f"Clerk ID:       {args.clerk_id}")
    print(f"Old user_id:    {args.old_user_id}")
    print(f"New user_id:    {new_user_id}")
    print()

    if args.old_user_id == new_user_id:
        print("Old and new user_id are the same — nothing to do.")
        return

    # Import settings and connect to Postgres
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from config import settings
    from db import PostgresManager

    if not settings.is_cloud_mode:
        print("ERROR: This script requires cloud mode (USE_CLOUD=true + DATABASE_URL).")
        sys.exit(1)

    pg = PostgresManager(settings.database_url)
    pg.connect()

    total_updated = 0
    for table in TABLES_WITH_USER_ID:
        try:
            # Count affected rows
            result = pg.execute(
                f"SELECT COUNT(*) FROM {table} WHERE user_id = %s",
                [args.old_user_id],
            ).fetchone()
            count = result[0] if result else 0

            if count == 0:
                print(f"  {table}: 0 rows (skip)")
                continue

            if args.dry_run:
                print(f"  {table}: {count} rows (would update)")
            else:
                pg.execute(
                    f"UPDATE {table} SET user_id = %s WHERE user_id = %s",
                    [new_user_id, args.old_user_id],
                )
                print(f"  {table}: {count} rows updated")

            total_updated += count
        except Exception as e:
            print(f"  {table}: ERROR - {e}")

    print()
    action = "would update" if args.dry_run else "updated"
    print(f"Total: {total_updated} rows {action}")

    pg.close()


if __name__ == "__main__":
    main()
