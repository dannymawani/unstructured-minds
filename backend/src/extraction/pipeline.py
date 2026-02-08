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
from .exercise_matcher import ExerciseMatcher
from .schemas import COMBINED_EXTRACTION_SCHEMA, EXTRACTION_SCHEMAS


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
    ) -> None:
        """Initialize extraction pipeline.

        Args:
            db: Database manager for storing extracted data
            claude: Claude client for AI extraction (optional)
        """
        self.db = db
        self.claude = claude
        self._schemas_dir = settings.data_path / "schemas"
        self._exercise_matcher = ExerciseMatcher(
            settings.data_path / "exercise_definitions.json"
        )

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
        result = self.db.execute(
            """
            SELECT file_hash FROM extraction_log
            WHERE file_path = ? AND success = TRUE
            ORDER BY extracted_at DESC LIMIT 1
            """,
            [file_path],
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
        self.db.execute(
            """
            INSERT INTO extraction_log (file_path, file_hash, success, error_message)
            VALUES (?, ?, ?, ?)
            """,
            [file_path, file_hash, success, error],
        )

    def _extract_date_from_path(self, file_path: str) -> Optional[str]:
        """Try to extract date from file path.

        Expects format like Daily-Notes/YYYY-MM/YYYY-MM-DD.md

        Args:
            file_path: Path to the file

        Returns:
            Date string or None
        """
        # Try to get filename as date
        parts = file_path.replace("\\", "/").split("/")
        filename = parts[-1].replace(".md", "")

        # Check if filename is a date
        try:
            datetime.strptime(filename, "%Y-%m-%d")
            return filename
        except ValueError:
            pass

        return None

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

        # Use REPLACE to handle updates
        self.db.execute(
            """
            INSERT OR REPLACE INTO daily_metrics
            (date, sleep_hours, sleep_quality, energy, mood, stress, notes, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                date,
                metrics.get("sleep_hours"),
                metrics.get("sleep_quality"),
                metrics.get("energy"),
                metrics.get("mood"),
                metrics.get("stress"),
                metrics.get("notes"),
                source_file,
            ],
        )
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

        records = 0
        for i, activity in enumerate(activities):
            activity_id = f"{date.replace('-', '')}_{activity.get('activity_type', 'other')}_{i+1}"

            # Insert activity record
            self.db.execute(
                """
                INSERT OR REPLACE INTO activities
                (id, date, activity_type, duration_minutes, notes, source_file)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    activity_id,
                    date,
                    activity.get("activity_type", "other"),
                    activity.get("duration_minutes"),
                    activity.get("notes"),
                    source_file,
                ],
            )

            # Insert exercise records
            for j, exercise in enumerate(activity.get("exercises", [])):
                exercise_id = self._generate_id()
                exercise_name = self._exercise_matcher.match(
                    exercise.get("name", "unknown")
                )[0]
                self.db.execute(
                    """
                    INSERT OR REPLACE INTO exercise_log
                    (id, activity_id, date, exercise_name, weight_kg, reps, set_number,
                     duration_minutes, distance_km, notes, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        exercise_id,
                        activity_id,
                        date,
                        exercise_name,
                        exercise.get("weight_kg"),
                        exercise.get("reps"),
                        j + 1,
                        exercise.get("duration_minutes"),
                        exercise.get("distance_km"),
                        exercise.get("notes"),
                        source_file,
                    ],
                )
                records += 1

        return records

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
        1. Load existing tasks for this source_file
        2. Skip any task whose normalized description already exists
        3. Remove stale backlog tasks from this file that are no longer in the note
        4. Insert genuinely new tasks

        Uses normalized descriptions to prevent duplicates when Claude
        extracts slightly different wording on re-extraction.

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

        # Load all existing tasks for this source file
        existing_rows = self.db.execute(
            "SELECT id, description, status FROM tasks WHERE source_file = ?",
            [source_file],
        ).fetchall()
        # Build lookup by normalized description -> (id, status, original_desc)
        existing_by_norm: dict[str, tuple[str, str, str]] = {
            self._normalize_task_desc(row[1]): (row[0], row[2], row[1])
            for row in existing_rows
        }

        # Collect normalized descriptions from current extraction
        new_norm_descriptions = {
            self._normalize_task_desc(task.get("description", ""))
            for task in tasks
        }

        # Remove stale backlog tasks that are no longer in the note
        # (keep done/cancelled/in_progress — those were acted on by the user)
        for norm_desc, (task_id, status, _orig) in existing_by_norm.items():
            if norm_desc not in new_norm_descriptions and status == "backlog":
                self.db.execute("DELETE FROM tasks WHERE id = ?", [task_id])

        records = 0
        for task in tasks:
            description = task.get("description", "")
            norm_desc = self._normalize_task_desc(description)

            # Skip if this task already exists for this source file
            if norm_desc in existing_by_norm:
                continue

            task_id = self._generate_id()
            raw_status = task.get("status", "todo")
            status = STATUS_MAP.get(raw_status, raw_status)
            completed_at = datetime.now() if status in ("done", "cancelled") else None

            self.db.execute(
                """
                INSERT INTO tasks
                (id, date, description, status, completed_at, category, priority, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    task_id,
                    date,
                    description,
                    status,
                    completed_at,
                    task.get("category"),
                    task.get("priority"),
                    source_file,
                ],
            )
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

        records = 0
        for meal in meals:
            meal_id = self._generate_id()
            self.db.execute(
                """
                INSERT INTO food_log
                (id, date, meal_type, time, description, calories,
                 protein_g, carbs_g, fat_g, notes, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    meal_id,
                    date,
                    meal.get("meal_type"),
                    meal.get("time"),
                    meal.get("description", ""),
                    meal.get("calories"),
                    meal.get("protein_g"),
                    meal.get("carbs_g"),
                    meal.get("fat_g"),
                    meal.get("notes"),
                    source_file,
                ],
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

        # Ensure custom_extractions table exists
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

        self.db.execute(
            """
            INSERT INTO custom_extractions
            (id, schema_name, date, data, source_file)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                extraction_id,
                schema_name,
                date,
                json.dumps(data),
                source_file,
            ],
        )

        return 1

    @staticmethod
    def _strip_suggestions(content: str) -> str:
        """Remove blockquoted workout suggestions before extraction.

        Strips lines that are part of a suggestion block (lines starting with >
        that follow a "> **Last session" header) so that suggested workouts
        are not mistakenly extracted as logged workouts.
        """
        lines = content.split("\n")
        result = []
        in_suggestion = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("> **Last session"):
                in_suggestion = True
                continue
            if in_suggestion:
                if stripped.startswith(">"):
                    continue
                in_suggestion = False
            result.append(line)
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

                if data.get("tasks"):
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
