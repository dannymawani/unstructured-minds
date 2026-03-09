"""Extraction pipeline for processing markdown notes."""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..claude import ClaudeClient
from ..config import settings
from ..db import DatabaseManager
from ..db.sql_compat import upsert, get_dialect
from ..logging_config import get_logger
from .exercise_matcher import ExerciseMatcher
from .schemas import COMBINED_EXTRACTION_SCHEMA, EXTRACTION_SCHEMAS

logger = get_logger(__name__)


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""

    success: bool
    file_path: str
    file_hash: str
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    records_inserted: dict[str, int] = field(default_factory=dict)


class ExtractionPipeline:
    """Pipeline for extracting structured data from markdown notes."""

    def __init__(
        self,
        db: DatabaseManager,
        claude: Optional[ClaudeClient] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Initialize extraction pipeline.

        Args:
            db: Database manager for storing extracted data
            claude: Claude client for AI extraction (optional)
            user_id: Authenticated user's UUID (used for Postgres inserts)
        """
        self.db = db
        self.claude = claude
        self.user_id = user_id
        # Try shared/ schemas first (checked into git), fall back to data/schemas/
        project_root = Path(__file__).resolve().parents[3]
        shared_schemas = project_root / "shared" / "schemas"
        self._schemas_dir = shared_schemas if shared_schemas.exists() else settings.data_path / "schemas"

        # Try shared/ exercise defs first
        shared_defs = project_root / "shared" / "exercise_definitions.json"
        exercise_defs_path = shared_defs if shared_defs.exists() else settings.data_path / "exercise_definitions.json"
        self._exercise_matcher = ExerciseMatcher(exercise_defs_path)
        self._exercise_matcher.load_ai_cache(settings.data_path / "ai_exercise_cache.json")

    def _load_custom_schema(self, name: str) -> Optional[dict[str, Any]]:
        """Load a custom schema from disk and convert to JSON Schema format.

        Args:
            name: Schema name

        Returns:
            JSON Schema dict or None if not found
        """
        path = self._schemas_dir / f"{name}.json"
        if not path.exists():
            return None

        try:
            with open(path) as f:
                schema_def = json.load(f)

            # Convert SchemaDefinition format to JSON Schema
            return self._convert_definition_to_json_schema(schema_def)
        except (json.JSONDecodeError, IOError, KeyError):
            return None

    def _convert_definition_to_json_schema(
        self, schema_def: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert a SchemaDefinition dict to JSON Schema format.

        Args:
            schema_def: Schema definition from file

        Returns:
            JSON Schema dict
        """
        properties = {}
        required = []

        for field in schema_def.get("fields", []):
            field_schema: dict[str, Any] = {"type": field["type"]}

            if field.get("description"):
                field_schema["description"] = field["description"]

            if field["type"] in ("integer", "number"):
                if field.get("min") is not None:
                    field_schema["minimum"] = field["min"]
                if field.get("max") is not None:
                    field_schema["maximum"] = field["max"]

            if field["type"] == "string" and field.get("enum"):
                field_schema["enum"] = field["enum"]

            if field["type"] == "array":
                field_schema["items"] = {"type": "string"}

            properties[field["name"]] = field_schema

            if field.get("required"):
                required.append(field["name"])

        json_schema: dict[str, Any] = {
            "type": "object",
            "description": schema_def.get("description", ""),
            "properties": properties,
        }

        if required:
            json_schema["required"] = required

        # Add extraction hints as a description enhancement if provided
        if schema_def.get("extraction_hints"):
            json_schema["description"] = (
                f"{json_schema['description']}\n\n"
                f"Extraction hints: {schema_def['extraction_hints']}"
            )

        return json_schema

    def get_schema(self, name: Optional[str] = None) -> dict[str, Any]:
        """Get a schema by name.

        Args:
            name: Schema name (None for combined/default schema)

        Returns:
            JSON Schema dict

        Raises:
            ValueError: If schema not found
        """
        if name is None or name == "combined":
            return COMBINED_EXTRACTION_SCHEMA

        # Check built-in schemas
        if name in EXTRACTION_SCHEMAS:
            return EXTRACTION_SCHEMAS[name]

        # Check custom schemas
        custom = self._load_custom_schema(name)
        if custom:
            return custom

        raise ValueError(f"Schema not found: {name}")

    def _compute_hash(self, content: str) -> str:
        """Compute hash of content for change detection.

        Args:
            content: File content

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def _should_extract(self, file_path: str, file_hash: str) -> bool:
        """Check if file needs extraction.

        Args:
            file_path: Path to the file
            file_hash: Hash of current content

        Returns:
            True if extraction needed
        """
        dialect = get_dialect(self.db)
        ph = "%s" if dialect == "postgres" else "?"
        conditions = [f"file_path = {ph}", f"success = TRUE"]
        params: list = [file_path]
        if dialect == "postgres" and self.user_id:
            conditions.append(f"user_id = {ph}")
            params.append(self.user_id)
        result = self.db.execute(
            f"SELECT file_hash FROM extraction_log WHERE {' AND '.join(conditions)} ORDER BY extracted_at DESC LIMIT 1",
            params,
        ).fetchall()
        if not result:
            return True
        return result[0][0] != file_hash

    def _log_extraction(
        self,
        file_path: str,
        file_hash: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log extraction attempt.

        Args:
            file_path: Path to the file
            file_hash: Hash of content
            success: Whether extraction succeeded
            error: Error message if failed
        """
        dialect = get_dialect(self.db)
        ph = "%s" if dialect == "postgres" else "?"
        cols = ["file_path", "file_hash", "success", "error_message"]
        vals: list = [file_path, file_hash, success, error]
        if dialect == "postgres" and self.user_id:
            cols.append("user_id")
            vals.append(self.user_id)
        placeholders = ", ".join([ph] * len(cols))
        self.db.execute(
            f"INSERT INTO extraction_log ({', '.join(cols)}) VALUES ({placeholders})",
            vals,
        )

    def _extract_date_from_path(self, file_path: str) -> Optional[str]:
        """Try to extract date from file path.

        Expects format like Daily-Notes/YYYY-MM/YYYY-MM-DD.md
        or YYYY/MM/YYYY-MM-DD-daily-note.md

        Args:
            file_path: Path to the file

        Returns:
            Date string or None
        """
        # Try to get filename as date
        parts = file_path.replace("\\", "/").split("/")
        filename = parts[-1].replace(".md", "")

        # Strip known suffixes like -daily-note
        clean_name = re.sub(r"-daily-note$", "", filename)

        # Check if filename (or cleaned name) is a date
        for name in [filename, clean_name]:
            try:
                datetime.strptime(name, "%Y-%m-%d")
                return name
            except ValueError:
                pass

        return None

    def _is_daily_note(self, file_path: str) -> bool:
        """Check if a file is a daily note based on path patterns.

        Daily notes match patterns like:
        - Daily-Notes/YYYY-MM/YYYY-MM-DD.md
        - YYYY/MM/YYYY-MM-DD-daily-note.md
        - Any file whose name (minus extension and -daily-note suffix) is a valid date

        Args:
            file_path: Path to the file

        Returns:
            True if the file is a daily note
        """
        parts = file_path.replace("\\", "/").split("/")
        filename = parts[-1].replace(".md", "")

        # Check known daily note directory prefixes
        if file_path.startswith("Daily-Notes/"):
            return True

        # Check if filename contains a date pattern (with optional suffix)
        clean_name = re.sub(r"-daily-note$", "", filename)
        try:
            datetime.strptime(clean_name, "%Y-%m-%d")
            return True
        except ValueError:
            pass

        return False

    def _generate_id(self) -> str:
        """Generate a unique ID.

        Returns:
            UUID string
        """
        return str(uuid.uuid4())

    def _store_daily_metrics(
        self,
        date: str,
        metrics: dict[str, Any],
        source_file: str,
    ) -> int:
        """Store daily metrics in database.

        Args:
            date: Date string
            metrics: Metrics data
            source_file: Source file path

        Returns:
            Number of records inserted
        """
        if not metrics:
            return 0

        dialect = get_dialect(self.db)
        cols = ["date", "sleep_hours", "sleep_quality", "energy", "mood", "stress", "weight_kg", "notes", "source_file"]
        conflict_cols = ["date"]
        vals: list = [
            date,
            metrics.get("sleep_hours"),
            metrics.get("sleep_quality"),
            metrics.get("energy"),
            metrics.get("mood"),
            metrics.get("stress"),
            metrics.get("weight_kg"),
            metrics.get("notes"),
            source_file,
        ]
        if dialect == "postgres" and self.user_id:
            cols.append("user_id")
            conflict_cols.append("user_id")
            vals.append(self.user_id)

        sql = upsert("daily_metrics", cols, conflict_cols, dialect=dialect)
        self.db.execute(sql, vals)
        return 1

    def _store_activities(
        self,
        date: str,
        activities: list[dict[str, Any]],
        source_file: str,
    ) -> int:
        """Store activities and exercises in database.

        Args:
            date: Date string
            activities: List of activity data
            source_file: Source file path

        Returns:
            Number of exercise records inserted
        """
        if not activities:
            return 0

        dialect = get_dialect(self.db)
        ph = "%s" if dialect == "postgres" else "?"

        # Delete old exercise + activity records for this date/source so
        # re-extraction doesn't leave stale rows behind.
        if dialect == "postgres" and self.user_id:
            self.db.execute(
                f"DELETE FROM exercise_log WHERE date = {ph} AND source_file = {ph} AND user_id = {ph}",
                [date, source_file, self.user_id],
            )
            self.db.execute(
                f"DELETE FROM activities WHERE date = {ph} AND source_file = {ph} AND user_id = {ph}",
                [date, source_file, self.user_id],
            )
        else:
            self.db.execute(
                f"DELETE FROM exercise_log WHERE date = {ph} AND source_file = {ph}",
                [date, source_file],
            )
            self.db.execute(
                f"DELETE FROM activities WHERE date = {ph} AND source_file = {ph}",
                [date, source_file],
            )

        records = 0
        for i, activity in enumerate(activities):
            activity_id = f"{date.replace('-', '')}_{activity.get('activity_type', 'other')}_{i+1}"

            # Insert activity record
            act_cols = ["id", "date", "activity_type", "duration_minutes", "notes", "source_file"]
            act_vals: list = [
                activity_id, date,
                activity.get("activity_type", "other"),
                activity.get("duration_minutes"),
                activity.get("notes"),
                source_file,
            ]
            if dialect == "postgres" and self.user_id:
                act_cols.append("user_id")
                act_vals.append(self.user_id)

            act_conflict = ["id", "user_id"] if (dialect == "postgres" and self.user_id) else ["id"]
            activity_sql = upsert("activities", act_cols, act_conflict, dialect=dialect)
            self.db.execute(activity_sql, act_vals)

            # Insert exercise records — one row per set
            global_set_num = 0
            for exercise in activity.get("exercises", []):
                raw_name = exercise.get("name", "unknown")
                if exercise.get("_name_from_note"):
                    # Name was restored from the original note — use it directly
                    # (only apply exact/alias/AI-cache matches, skip fuzzy to prevent mis-mapping)
                    canonical, confidence = self._exercise_matcher.match(raw_name)
                    exercise_name = canonical if confidence >= 0.95 else raw_name.strip().title()
                else:
                    exercise_name = self._exercise_matcher.match(raw_name)[0]

                sets_data = exercise.get("sets", [])
                if sets_data and isinstance(sets_data, list) and isinstance(sets_data[0], dict):
                    # New format: per-set array with individual weights/reps
                    for set_entry in sets_data:
                        global_set_num += 1
                        exercise_id = self._generate_id()
                        ex_cols = ["id", "activity_id", "date", "exercise_name", "weight_kg", "reps", "set_number",
                                   "duration_minutes", "distance_km", "notes", "source_file"]
                        ex_vals: list = [
                            exercise_id, activity_id, date, exercise_name,
                            set_entry.get("weight_kg"),
                            set_entry.get("reps"),
                            global_set_num,
                            exercise.get("duration_minutes"),
                            exercise.get("distance_km"),
                            exercise.get("notes"),
                            source_file,
                        ]
                        if dialect == "postgres" and self.user_id:
                            ex_cols.append("user_id")
                            ex_vals.append(self.user_id)

                        ex_conflict = ["id", "user_id"] if (dialect == "postgres" and self.user_id) else ["id"]
                        exercise_sql = upsert("exercise_log", ex_cols, ex_conflict, dialect=dialect)
                        self.db.execute(exercise_sql, ex_vals)
                        records += 1
                else:
                    # Legacy format: single row with top-level weight_kg/reps
                    global_set_num += 1
                    exercise_id = self._generate_id()
                    ex_cols = ["id", "activity_id", "date", "exercise_name", "weight_kg", "reps", "set_number",
                               "duration_minutes", "distance_km", "notes", "source_file"]
                    ex_vals = [
                        exercise_id, activity_id, date, exercise_name,
                        exercise.get("weight_kg"),
                        exercise.get("reps"),
                        global_set_num,
                        exercise.get("duration_minutes"),
                        exercise.get("distance_km"),
                        exercise.get("notes"),
                        source_file,
                    ]
                    if dialect == "postgres" and self.user_id:
                        ex_cols.append("user_id")
                        ex_vals.append(self.user_id)

                    ex_conflict = ["id", "user_id"] if (dialect == "postgres" and self.user_id) else ["id"]
                    exercise_sql = upsert("exercise_log", ex_cols, ex_conflict, dialect=dialect)
                    self.db.execute(exercise_sql, ex_vals)
                    records += 1

        return records

    async def _auto_label_new_exercises(self, activities: list[dict]) -> None:
        """Auto-classify exercises that have no muscle group data.

        For each exercise name not in definitions or community_exercises,
        calls Claude to generate muscle groups/category and inserts into
        community_exercises so they're available for all users.
        """
        if not self.claude or not self.claude.is_configured:
            return

        # Collect unique exercise names from this extraction
        exercise_names: set[str] = set()
        for activity in activities:
            for exercise in activity.get("exercises", []):
                raw_name = exercise.get("name", "")
                if raw_name:
                    canonical, _ = self._exercise_matcher.match(raw_name)
                    exercise_names.add(canonical)

        # Find ones with no muscle groups (not in definitions or community)
        unlabeled = [
            name for name in exercise_names
            if not self._exercise_matcher.get_muscle_groups(name)
        ]
        if not unlabeled:
            return

        # Get existing muscle groups and categories for consistency
        all_meta = [self._exercise_matcher.get_metadata(n) for n in self._exercise_matcher.canonical_names]
        known_muscles = sorted({mg for m in all_meta for mg in m["muscle_groups"]})
        known_categories = sorted({m["category"] for m in all_meta})

        try:
            results = await self.claude.label_new_exercises(
                exercise_names=unlabeled,
                known_muscle_groups=known_muscles,
                known_categories=known_categories,
            )
        except Exception as e:
            logger.warning("auto_label_exercises_failed", error=str(e))
            return

        dialect = get_dialect(self.db)
        ph = "%s" if dialect == "postgres" else "?"

        for entry in results:
            if not entry.get("is_exercise", True):
                continue
            if not entry.get("muscle_groups"):
                continue

            key = entry["key"]
            display = entry["display"]
            muscle_groups = entry["muscle_groups"]
            category = entry.get("category", "other")
            recovery_hours = entry.get("recovery_hours", 48)

            # Check if already exists in community_exercises
            try:
                existing = self.db.execute(
                    f"SELECT exercise_key FROM community_exercises WHERE exercise_key = {ph}",
                    [key],
                ).fetchone()
                if existing:
                    continue
            except Exception:
                continue

            # Insert into community_exercises
            try:
                muscle_groups_val = json.dumps(muscle_groups)
                self.db.execute(
                    f"""INSERT INTO community_exercises
                        (exercise_key, display_name, aliases, muscle_groups, category, recovery_hours)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})""",
                    [key, display, json.dumps([]), muscle_groups_val, category, recovery_hours],
                )

                # Update in-memory matcher immediately
                self._exercise_matcher.load_community_exercises([{
                    "exercise_key": key,
                    "display_name": display,
                    "aliases": [],
                    "muscle_groups": muscle_groups,
                    "category": category,
                    "recovery_hours": recovery_hours,
                }])

                logger.info("auto_labeled_exercise", key=key, display=display, muscle_groups=muscle_groups)
            except Exception as e:
                logger.warning("auto_label_insert_failed", key=key, error=str(e))

    @staticmethod
    def _normalize_task_desc(desc: str) -> str:
        """Normalize a task description for dedup comparison.

        Strips whitespace, lowercases, and removes minor punctuation differences
        so that Claude re-extracting the same task with slight wording changes
        still matches the existing record.
        """
        desc = desc.strip().lower()
        # Collapse whitespace
        desc = re.sub(r"\s+", " ", desc)
        # Remove trailing punctuation that doesn't change meaning
        desc = desc.rstrip(".,;:!?")
        return desc

    def _store_tasks(
        self,
        date: str,
        tasks: list[dict[str, Any]],
        source_file: str,
    ) -> int:
        """Store tasks in database, respecting previously completed tasks.

        On re-extraction:
        1. Check ALL existing tasks (globally, not just this file) for dedup
        2. Skip any task whose normalized description already exists anywhere
        3. Remove stale backlog tasks from this file that are no longer in the note
        4. Insert genuinely new tasks
        5. Update source_file on existing tasks if this note is newer

        Uses normalized descriptions to prevent duplicates when the same task
        appears in multiple daily notes (e.g. rolled-over tasks).

        Args:
            date: Date string
            tasks: List of task data
            source_file: Source file path

        Returns:
            Number of records inserted
        """
        if not tasks:
            return 0

        # Map extraction statuses to API-standard values
        STATUS_MAP = {
            "todo": "backlog",
            "done": "done",
            "in_progress": "in_progress",
            "cancelled": "cancelled",
        }

        dialect = get_dialect(self.db)
        ph = "%s" if dialect == "postgres" else "?"

        # Load ALL existing tasks for this user (global dedup, not per-file)
        global_conds: list[str] = []
        global_params: list = []
        if dialect == "postgres" and self.user_id:
            global_conds.append(f"user_id = {ph}")
            global_params.append(self.user_id)
        global_where = f"WHERE {' AND '.join(global_conds)}" if global_conds else ""
        global_rows = self.db.execute(
            f"SELECT id, description, status, source_file, date FROM tasks {global_where}",
            global_params,
        ).fetchall()
        # Build lookup by normalized description -> (id, status, source_file, date)
        global_by_norm: dict[str, tuple[str, str, str, str]] = {
            self._normalize_task_desc(row[1]): (row[0], row[2], row[3], str(row[4]))
            for row in global_rows
        }

        # Also build per-file lookup for stale task cleanup
        file_by_norm: dict[str, tuple[str, str]] = {
            self._normalize_task_desc(row[1]): (row[0], row[2])
            for row in global_rows
            if row[3] == source_file
        }

        # Collect normalized descriptions from current extraction
        new_norm_descriptions = {
            self._normalize_task_desc(task.get("description", ""))
            for task in tasks
        }

        # Remove stale backlog tasks from THIS file that are no longer in the note
        for norm_desc, (task_id, status) in file_by_norm.items():
            if norm_desc not in new_norm_descriptions and status == "backlog":
                del_conds = [f"id = {ph}"]
                del_params: list = [task_id]
                if dialect == "postgres" and self.user_id:
                    del_conds.append(f"user_id = {ph}")
                    del_params.append(self.user_id)
                self.db.execute(f"DELETE FROM tasks WHERE {' AND '.join(del_conds)}", del_params)

        records = 0
        for task in tasks:
            description = task.get("description", "")
            norm_desc = self._normalize_task_desc(description)

            # Skip if this task already exists ANYWHERE for this user
            if norm_desc in global_by_norm:
                existing_id, existing_status, existing_file, existing_date = global_by_norm[norm_desc]
                # Update source_file to the latest note if this note is newer
                if date > existing_date and existing_file != source_file:
                    upd_conds = [f"id = {ph}"]
                    upd_params: list = [existing_id]
                    if dialect == "postgres" and self.user_id:
                        upd_conds.append(f"user_id = {ph}")
                        upd_params.append(self.user_id)
                    self.db.execute(
                        f"UPDATE tasks SET source_file = {ph}, date = {ph} WHERE {' AND '.join(upd_conds)}",
                        [source_file, date] + upd_params,
                    )
                continue

            task_id = self._generate_id()
            raw_status = task.get("status", "todo")
            status = STATUS_MAP.get(raw_status, raw_status)
            completed_at = datetime.now() if status in ("done", "cancelled") else None

            cols = ["id", "date", "description", "status", "completed_at", "category", "priority", "source_file"]
            vals: list = [
                task_id, date, description, status, completed_at,
                task.get("category"), task.get("priority"), source_file,
            ]
            if dialect == "postgres" and self.user_id:
                cols.append("user_id")
                vals.append(self.user_id)

            placeholders = ", ".join([ph] * len(cols))
            self.db.execute(
                f"INSERT INTO tasks ({', '.join(cols)}) VALUES ({placeholders})",
                vals,
            )
            # Track newly inserted tasks in global lookup to prevent
            # duplicates within the same extraction batch
            global_by_norm[norm_desc] = (task_id, status, source_file, date)
            records += 1

        return records

    def _store_meals(
        self,
        date: str,
        meals: list[dict[str, Any]],
        source_file: str,
    ) -> int:
        """Store food log entries in database.

        Args:
            date: Date string
            meals: List of meal data
            source_file: Source file path

        Returns:
            Number of records inserted
        """
        if not meals:
            return 0

        dialect = get_dialect(self.db)
        ph = "%s" if dialect == "postgres" else "?"

        # Delete old meal records for this date/source so re-extraction
        # doesn't leave duplicates.
        if dialect == "postgres" and self.user_id:
            self.db.execute(
                f"DELETE FROM food_log WHERE date = {ph} AND source_file = {ph} AND user_id = {ph}",
                [date, source_file, self.user_id],
            )
        else:
            self.db.execute(
                f"DELETE FROM food_log WHERE date = {ph} AND source_file = {ph}",
                [date, source_file],
            )

        records = 0
        for meal in meals:
            meal_id = self._generate_id()
            cols = ["id", "date", "meal_type", "time", "description", "calories",
                    "protein_g", "carbs_g", "fat_g", "notes", "source_file"]
            vals: list = [
                meal_id, date,
                meal.get("meal_type"),
                meal.get("time"),
                meal.get("description", ""),
                meal.get("calories"),
                meal.get("protein_g"),
                meal.get("carbs_g"),
                meal.get("fat_g"),
                meal.get("notes"),
                source_file,
            ]
            if dialect == "postgres" and self.user_id:
                cols.append("user_id")
                vals.append(self.user_id)
            placeholders = ", ".join([ph] * len(cols))
            self.db.execute(
                f"INSERT INTO food_log ({', '.join(cols)}) VALUES ({placeholders})",
                vals,
            )
            records += 1

        return records

    def _store_custom_extraction(
        self,
        schema_name: str,
        date: str,
        data: dict[str, Any],
        source_file: str,
    ) -> int:
        """Store custom schema extracted data as JSON.

        Custom schema data is stored in a generic custom_extractions table
        as JSON for flexibility.

        Args:
            schema_name: Name of the custom schema
            date: Date string
            data: Extracted data
            source_file: Source file path

        Returns:
            Number of records inserted
        """
        if not data:
            return 0

        extraction_id = self._generate_id()
        dialect = get_dialect(self.db)
        ph = "%s" if dialect == "postgres" else "?"

        # Ensure custom_extractions table exists (DuckDB only; Postgres schema managed separately)
        if dialect != "postgres":
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_extractions (
                    id VARCHAR PRIMARY KEY,
                    schema_name VARCHAR NOT NULL,
                    date DATE,
                    data JSON NOT NULL,
                    source_file VARCHAR,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        cols = ["id", "schema_name", "date", "data", "source_file"]
        vals: list = [extraction_id, schema_name, date, json.dumps(data), source_file]
        if dialect == "postgres" and self.user_id:
            cols.append("user_id")
            vals.append(self.user_id)
        placeholders = ", ".join([ph] * len(cols))
        self.db.execute(
            f"INSERT INTO custom_extractions ({', '.join(cols)}) VALUES ({placeholders})",
            vals,
        )

        return 1

    @staticmethod
    @staticmethod
    def _parse_exercise_names_from_content(content: str) -> list[str]:
        """Parse original exercise names from structured markdown content.

        Looks for lines matching patterns like:
          * Exercise Name: 1x8 @ 20kg, ...
          * Exercise Name: sets...
          - Exercise Name: ...

        Returns list of exercise names as written by the user.
        """
        names: list[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            # Match bullet lines with exercise data (colon followed by set/rep info)
            if stripped.startswith(("* ", "- ")):
                text = stripped[2:].strip()
                # Skip bold-prefixed metadata lines like "* **Type**: Strength"
                if text.startswith("**") and "**:" in text:
                    continue
                # Skip checkbox lines
                if text.startswith("[ ]") or text.startswith("[x]"):
                    continue
                # Look for "Name: <set data>" pattern
                colon_idx = text.find(":")
                if colon_idx > 0:
                    after_colon = text[colon_idx + 1:].strip()
                    # Verify it looks like exercise data (has digits for reps/weight)
                    if re.search(r"\d+x\d+|\d+\s*kg|\d+\s*rep", after_colon, re.IGNORECASE):
                        names.append(text[:colon_idx].strip())
                elif re.search(r"\d+x\d+|\d+\s*kg", text):
                    # Line without colon but with exercise data (e.g. "* GHD Crunches 1x12")
                    match = re.match(r"^(.+?)\s*\d+x\d+", text)
                    if match:
                        names.append(match.group(1).strip())
        return names

    @staticmethod
    def _restore_original_exercise_names(
        content: str, activities: list[dict],
    ) -> list[dict]:
        """Replace Claude-renamed exercise names with the user's original names.

        Claude sometimes renames exercises (e.g. 'Biceps Preacher Cable Curl' ->
        'Biceps Cable Curl'). This parses the original names from the note and
        restores them using fuzzy matching.
        """
        from difflib import SequenceMatcher

        original_names = ExtractionPipeline._parse_exercise_names_from_content(content)
        if not original_names:
            return activities

        for activity in activities:
            for exercise in activity.get("exercises", []):
                claude_name = exercise.get("name", "")
                if not claude_name:
                    continue

                claude_lower = claude_name.lower().strip()

                # Check if Claude's name exactly matches an original — keep it, but mark it
                if any(n.lower().strip() == claude_lower for n in original_names):
                    exercise["_name_from_note"] = True
                    continue

                # Find the best matching original name
                best_score = 0.0
                best_name = None
                for orig in original_names:
                    score = SequenceMatcher(
                        None, claude_lower, orig.lower().strip()
                    ).ratio()
                    if score > best_score:
                        best_score = score
                        best_name = orig

                # Restore original name if it's a close-enough match
                if best_name and best_score >= 0.55:
                    exercise["name"] = best_name
                    exercise["_name_from_note"] = True

        return activities

    @staticmethod
    def _strip_suggestions(content: str) -> str:
        """Remove blockquoted workout suggestion tables before extraction.

        Strips any contiguous blockquote block (lines starting with >) that
        contains a markdown table (pipe characters). This catches all header
        variants — "> **Last session", "> **Suggested Workout**", etc.
        """
        lines = content.split("\n")
        result: list[str] = []
        block: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(">"):
                block.append(line)
            else:
                if block:
                    # Keep the block only if it doesn't look like a suggestion table
                    has_table = any("|" in l for l in block)
                    if not has_table:
                        result.extend(block)
                    block = []
                result.append(line)
        # Handle trailing blockquote
        if block:
            has_table = any("|" in l for l in block)
            if not has_table:
                result.extend(block)
        return "\n".join(result)

    async def extract(
        self,
        file_path: str,
        content: str,
        force: bool = False,
        schema_name: Optional[str] = None,
    ) -> ExtractionResult:
        """Extract structured data from markdown content.

        Args:
            file_path: Path to the file (for logging/deduplication)
            content: Markdown content to extract from
            force: Force extraction even if already processed
            schema_name: Optional schema name to use for extraction

        Returns:
            Extraction result
        """
        file_hash = self._compute_hash(content)

        # Check if already extracted
        if not force and not self._should_extract(file_path, file_hash):
            return ExtractionResult(
                success=True,
                file_path=file_path,
                file_hash=file_hash,
                data=None,
                error="Already extracted (no changes)",
            )

        # Check if Claude is available
        if not self.claude or not self.claude.is_configured:
            return ExtractionResult(
                success=False,
                file_path=file_path,
                file_hash=file_hash,
                error="Claude API not configured",
            )

        try:
            # Get the schema to use
            try:
                schema = self.get_schema(schema_name)
            except ValueError as e:
                return ExtractionResult(
                    success=False,
                    file_path=file_path,
                    file_hash=file_hash,
                    error=str(e),
                )

            # Strip suggestion blocks before extraction
            clean_content = self._strip_suggestions(content)

            # Extract data using Claude
            data = await self.claude.extract(clean_content, schema)

            # Restore original exercise names that Claude may have renamed
            if data.get("activities"):
                data["activities"] = self._restore_original_exercise_names(
                    content, data["activities"]
                )

            # Get date from file path first (reliable), then fall back to extracted data
            date = self._extract_date_from_path(file_path) or data.get("date")
            if not date:
                # Use today if no date found
                date = datetime.now().strftime("%Y-%m-%d")

            # Store extracted data
            records_inserted = {}

            # Check if this is a custom schema extraction
            is_custom_schema = (
                schema_name is not None
                and schema_name not in EXTRACTION_SCHEMAS
                and schema_name != "combined"
            )

            if is_custom_schema:
                # Store as custom extraction
                records_inserted["custom"] = self._store_custom_extraction(
                    schema_name, date, data, file_path
                )
            else:
                # Standard built-in schema extraction
                if data.get("daily_metrics"):
                    records_inserted["daily_metrics"] = self._store_daily_metrics(
                        date, data["daily_metrics"], file_path
                    )

                if data.get("activities"):
                    records_inserted["exercises"] = self._store_activities(
                        date, data["activities"], file_path
                    )
                    # Auto-classify new exercises that have no muscle groups
                    await self._auto_label_new_exercises(data["activities"])

                if data.get("tasks") and self._is_daily_note(file_path):
                    records_inserted["tasks"] = self._store_tasks(
                        date, data["tasks"], file_path
                    )

                if data.get("meals"):
                    records_inserted["meals"] = self._store_meals(
                        date, data["meals"], file_path
                    )

            # Log successful extraction
            self._log_extraction(file_path, file_hash, True)

            return ExtractionResult(
                success=True,
                file_path=file_path,
                file_hash=file_hash,
                data=data,
                records_inserted=records_inserted,
            )

        except Exception as e:
            # Log failed extraction
            self._log_extraction(file_path, file_hash, False, str(e))

            return ExtractionResult(
                success=False,
                file_path=file_path,
                file_hash=file_hash,
                error=str(e),
            )
