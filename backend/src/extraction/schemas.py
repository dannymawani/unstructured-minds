"""Extraction schemas for Claude tool use.

These schemas define the structure Claude should extract from markdown notes.
"""

from typing import Any


# Schema for extracting exercise/workout data
EXERCISE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "activities": {
            "type": "array",
            "description": (
                "List of workout activities ACTUALLY PERFORMED as logged in the note. "
                "Ignore any exercises in blockquotes (> prefix) — those are suggestions, not completed workouts. "
                "Only extract exercises the user explicitly logged with weights, reps, and sets."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "activity_type": {
                        "type": "string",
                        "enum": ["strength", "bjj", "cardio", "yoga", "walk", "recovery", "other"],
                        "description": "Type of activity",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration in minutes",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes about the activity",
                    },
                    "exercises": {
                        "type": "array",
                        "description": "Individual exercises performed",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": (
                                        "Exercise name. Use standard English names like: "
                                        "Deadlift, Squat, Bench Press, Military Press, "
                                        "Leg Press, Leg Curl, Leg Extension, Pulldown, "
                                        "Barbell Row, Dumbbell Row, Incline Dumbbell Press, "
                                        "Kettlebell Swing, Triceps Rope Extension, "
                                        "Biceps Cable Curl, Good Mornings, Cossack Squats"
                                    ),
                                },
                                "weight_kg": {"type": "number", "description": "Weight in kg"},
                                "reps": {"type": "integer", "description": "Number of reps"},
                                "sets": {"type": "integer", "description": "Number of sets"},
                                "duration_minutes": {"type": "integer", "description": "Duration in minutes"},
                                "distance_km": {"type": "number", "description": "Distance in km"},
                            },
                            "required": ["name"],
                        },
                    },
                },
                "required": ["activity_type"],
            },
        },
    },
    "required": ["activities"],
}


# Schema for extracting daily health metrics
DAILY_METRICS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sleep_hours": {
            "type": "number",
            "description": "Hours of sleep",
        },
        "sleep_quality": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Sleep quality rating 1-10",
        },
        "energy": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Energy level rating 1-10",
        },
        "mood": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Mood rating 1-10",
        },
        "stress": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Stress level rating 1-10",
        },
        "notes": {
            "type": "string",
            "description": "Additional notes about the day",
        },
    },
}


# Schema for extracting tasks
TASKS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "description": "List of tasks found in the note",
            "items": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Task description",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["todo", "done", "in_progress", "cancelled"],
                        "description": "Task status",
                    },
                    "category": {
                        "type": "string",
                        "description": "Task category (work, personal, etc.)",
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Priority 1-5 (1=highest)",
                    },
                },
                "required": ["description", "status"],
            },
        },
    },
    "required": ["tasks"],
}


# Schema for extracting food log entries
FOOD_LOG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "meals": {
            "type": "array",
            "description": "List of meals/food entries",
            "items": {
                "type": "object",
                "properties": {
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                        "description": "Type of meal",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time of meal (HH:MM)",
                    },
                    "description": {
                        "type": "string",
                        "description": "What was eaten",
                    },
                    "calories": {
                        "type": "integer",
                        "description": "Estimated calories",
                    },
                    "protein_g": {
                        "type": "integer",
                        "description": "Protein in grams",
                    },
                    "carbs_g": {
                        "type": "integer",
                        "description": "Carbohydrates in grams",
                    },
                    "fat_g": {
                        "type": "integer",
                        "description": "Fat in grams",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes",
                    },
                },
                "required": ["description"],
            },
        },
    },
    "required": ["meals"],
}


# Combined schema for extracting all data types at once
COMBINED_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Extract structured data from a daily note",
    "properties": {
        "date": {
            "type": "string",
            "description": "Date of the note in YYYY-MM-DD format",
        },
        "daily_metrics": {
            "type": "object",
            "description": "Health and wellness metrics for the day",
            "properties": DAILY_METRICS_SCHEMA["properties"],
        },
        "activities": EXERCISE_SCHEMA["properties"]["activities"],
        "tasks": TASKS_SCHEMA["properties"]["tasks"],
        "meals": FOOD_LOG_SCHEMA["properties"]["meals"],
    },
    "required": [],
}


# Registry of available schemas
EXTRACTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "exercise": EXERCISE_SCHEMA,
    "daily_metrics": DAILY_METRICS_SCHEMA,
    "tasks": TASKS_SCHEMA,
    "food_log": FOOD_LOG_SCHEMA,
    "combined": COMBINED_EXTRACTION_SCHEMA,
}


def get_schema(name: str) -> dict[str, Any]:
    """Get a schema by name.

    Args:
        name: Schema name

    Returns:
        Schema dictionary

    Raises:
        KeyError: If schema not found
    """
    if name not in EXTRACTION_SCHEMAS:
        raise KeyError(f"Unknown schema: {name}. Available: {list(EXTRACTION_SCHEMAS.keys())}")
    return EXTRACTION_SCHEMAS[name]
