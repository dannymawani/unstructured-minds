#!/usr/bin/env python3
"""Seed Postgres vault_files table from a local vault/ directory.

One-time migration script for users moving from local to cloud mode.

Usage:
    python -m scripts.seed_vault                          # defaults: ../vault, env DATABASE_URL
    python -m scripts.seed_vault --vault-path /path/to/vault
    python -m scripts.seed_vault --dry-run                # preview only
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Add backend/ to path so we can import src.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.postgres import PostgresManager
from src.db.postgres_schema import init_postgres_schema


DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001")


def seed_vault(vault_path: Path, database_url: str, user_id: str, dry_run: bool = False) -> int:
    """Insert all files from vault_path into Postgres vault_files table.

    Returns:
        Number of files seeded.
    """
    if not vault_path.is_dir():
        print(f"Error: vault path does not exist: {vault_path}")
        return 0

    pg = PostgresManager(database_url)
    pg.connect()
    init_postgres_schema(pg, user_id)

    count = 0
    for file_path in sorted(vault_path.rglob("*")):
        if not file_path.is_file():
            continue

        relative = str(file_path.relative_to(vault_path))
        try:
            content = file_path.read_bytes()
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            print(f"  SKIP (binary): {relative}")
            continue

        size = len(content)
        content_hash = hashlib.sha256(content).hexdigest()

        if dry_run:
            print(f"  [dry-run] {relative} ({size:,} bytes)")
        else:
            pg.execute(
                """
                INSERT INTO vault_files (user_id, path, content, size_bytes, content_hash, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, path) DO UPDATE
                SET content = EXCLUDED.content,
                    size_bytes = EXCLUDED.size_bytes,
                    content_hash = EXCLUDED.content_hash,
                    updated_at = NOW()
                """,
                [user_id, relative, text, size, content_hash],
            )
            print(f"  OK: {relative} ({size:,} bytes)")

        count += 1

    pg.close()
    return count


def main():
    parser = argparse.ArgumentParser(description="Seed Postgres vault_files from local vault directory")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "vault",
        help="Path to local vault directory (default: ../vault)",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Postgres connection string (default: DATABASE_URL env var)",
    )
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"User UUID (default: {DEFAULT_USER_ID})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files without writing to Postgres",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("Error: DATABASE_URL not set. Pass --database-url or set the env var.")
        sys.exit(1)

    print(f"Vault path:   {args.vault_path}")
    print(f"Database URL: {args.database_url[:30]}...")
    print(f"User ID:      {args.user_id}")
    print(f"Dry run:      {args.dry_run}")
    print()

    count = seed_vault(args.vault_path, args.database_url, args.user_id, args.dry_run)
    action = "found" if args.dry_run else "seeded"
    print(f"\nDone: {count} files {action}.")


if __name__ == "__main__":
    main()
