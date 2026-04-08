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
                        "enum": ["strength", "bjj", "cardio", "running", "cycling", "swimming", "yoga", "walk", "recovery", "other"],
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
                                        "Exercise name exactly as written by the user. "
                                        "Preserve the user's original exercise name including any qualifiers "
                                        "(e.g., 'Zercher Jefferson Curl', 'Biceps Preacher Cable Curl'). "
                                        "Do not rename, simplify, or standardize exercise names."
                                    ),
                                },
                                "sets": {
                                    "type": "array",
                                    "description": (
                                        "Individual sets performed for this exercise. "
                                        "Each set has its own weight and reps. "
                                        "For example, '1x8 @ 20kg, 1x8 @ 40kg, 1x6 @ 60kg' becomes three set entries. "
                                        "If the user writes '3x8 @ 80kg', expand to three identical set entries."
                                    ),
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "weight_kg": {"type": "number", "description": "Weight in kg for this set"},
                                            "reps": {"type": "integer", "description": "Number of reps for this set"},
                                        },
                                    },
                                },
                                "weight_kg": {"type": "number", "description": "Weight in kg (legacy, prefer sets array)"},
                                "reps": {"type": "integer", "description": "Number of reps (legacy, prefer sets array)"},
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
        "weight_kg": {
            "type": "number",
            "description": "Body weight in kilograms, if mentioned",
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
            "description": (
                "List of meals/food entries. For EVERY meal, you MUST estimate "
                "calories and macronutrients (protein, carbs, fat) based on the "
                "food description, even if the user did not provide numbers. "
                "Use your nutritional knowledge to provide reasonable estimates "
                "for typical serving sizes."
            ),
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
                        "description": "What was eaten — include all items mentioned",
                    },
                    "calories": {
                        "type": "integer",
                        "description": (
                            "Total estimated calories for this meal. "
                            "ALWAYS provide an estimate even if the user didn't specify — "
                            "use standard nutritional data for typical serving sizes."
                        ),
                    },
                    "protein_g": {
                        "type": "integer",
                        "description": (
                            "Estimated protein in grams. "
                            "ALWAYS estimate based on the foods described."
                        ),
                    },
                    "carbs_g": {
                        "type": "integer",
                        "description": (
                            "Estimated carbohydrates in grams. "
                            "ALWAYS estimate based on the foods described."
                        ),
                    },
                    "fat_g": {
                        "type": "integer",
                        "description": (
                            "Estimated fat in grams. "
                            "ALWAYS estimate based on the foods described."
                        ),
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes",
                    },
                },
                "required": ["description", "calories", "protein_g", "carbs_g", "fat_g"],
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
