"""Migrate kanban markdown files into DuckDB kanban_tasks table.

Reads all .md files from implementation_plan/kanban/{not_started,in_progress,done}/,
parses their YAML-like frontmatter, and inserts them into the kanban_tasks table.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

import duckdb


KANBAN_BASE = project_root / "implementation_plan" / "kanban"
DB_PATH = project_root / "data" / "unstructured_minds.duckdb"

STATUS_FOLDERS = {
    "not_started": "not_started",
    "in_progress": "in_progress",
    "done": "done",
}


def parse_frontmatter(content: str) -> dict:
    """Extract key-value pairs from markdown frontmatter-style metadata."""
    result = {}

    patterns = {
        "phase": r"\*\*Phase:\*\*\s*(.+)",
        "priority": r"\*\*Priority:\*\*\s*(.+)",
        "status": r"\*\*Status:\*\*\s*(.+)",
        "branch": r"\*\*Branch:\*\*\s*(.+)",
        "depends_on": r"\*\*Depends On:\*\*\s*(.+)",
        "completed": r"\*\*Completed:\*\*\s*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            result[key] = match.group(1).strip()

    # Extract title from first H1
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        result["title"] = title_match.group(1).strip()

    # Extract description
    desc_match = re.search(r"## Description\n\n(.+?)(?:\n\n|\Z)", content, re.DOTALL)
    if desc_match:
        result["description"] = desc_match.group(1).strip()

    return result


def migrate():
    """Run the migration."""
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(DB_PATH))

    # Create table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kanban_tasks (
            id VARCHAR PRIMARY KEY,
            title VARCHAR NOT NULL,
            phase VARCHAR,
            priority VARCHAR,
            status VARCHAR NOT NULL DEFAULT 'not_started',
            branch VARCHAR,
            depends_on VARCHAR,
            description VARCHAR,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Clear existing data
    conn.execute("DELETE FROM kanban_tasks")

    inserted = 0
    errors = 0

    for folder_name, status in STATUS_FOLDERS.items():
        folder = KANBAN_BASE / folder_name
        if not folder.exists():
            continue

        for filepath in sorted(folder.glob("*.md")):
            if filepath.name.startswith("README"):
                continue

            try:
                content = filepath.read_text()
                meta = parse_frontmatter(content)

                task_id = filepath.stem
                title = meta.get("title", filepath.stem)
                phase = meta.get("phase")
                priority = meta.get("priority")
                branch = meta.get("branch")
                depends_on = meta.get("depends_on")
                description = meta.get("description")
                completed_str = meta.get("completed")
                completed_at = None
                if completed_str:
                    try:
                        completed_at = datetime.strptime(completed_str, "%Y-%m-%d")
                    except ValueError:
                        pass

                conn.execute(
                    """INSERT INTO kanban_tasks
                       (id, title, phase, priority, status, branch, depends_on, description, content, completed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [task_id, title, phase, priority, status, branch, depends_on, description, content, completed_at],
                )
                inserted += 1
            except Exception as e:
                print(f"  ERROR: {filepath.name}: {e}")
                errors += 1

    conn.close()

    print(f"\nMigration complete:")
    print(f"  Inserted: {inserted}")
    print(f"  Errors:   {errors}")
    print(f"  Database: {DB_PATH}")


if __name__ == "__main__":
    migrate()
