---
name: extract-data
description: Extract structured data from markdown notes using Claude API patterns. Reference for implementing extraction logic.
user-invocable: false
---

# Data Extraction Patterns

This skill provides reference patterns for extracting structured data from natural language markdown notes.

## Core Principle

Users write naturally in markdown. The system uses Claude to extract structured data into JSON/CSV for DuckDB storage.

## Extraction Flow

```
Markdown Note → Parse Sections → Claude API → JSON → Validate → DuckDB
```

## Example Input (Daily Note)

```markdown
# 2026-01-15

## Training
Did a solid strength session today. Started with squats - worked up to 3x5 at 100kg, felt strong.
Then bench press 3x8 at 70kg. Finished with some lat pulldowns and face pulls.

## Food
- Breakfast: Oatmeal with banana and peanut butter, coffee
- Lunch: Chicken salad with quinoa, about 500 cal
- Dinner: Salmon with roasted vegetables, rice

## Tasks
- [x] Review PR for auth module
- [x] Fix the login bug
- [ ] Write tests for extraction -> moved to tomorrow
- [ ] Call dentist
```

## Expected Extraction

### Activities
```json
[
  {"id": "20260115_str_1", "date": "2026-01-15", "activity_type": "str", "duration_minutes": 60}
]
```

### Exercise Log
```json
[
  {"id": "20260115_str_1_squat_1", "activity_id": "20260115_str_1", "date": "2026-01-15",
   "exercise_name": "squat", "set_number": 1, "reps": 5, "weight_kg": 100},
  {"id": "20260115_str_1_squat_2", "activity_id": "20260115_str_1", "date": "2026-01-15",
   "exercise_name": "squat", "set_number": 2, "reps": 5, "weight_kg": 100},
  {"id": "20260115_str_1_squat_3", "activity_id": "20260115_str_1", "date": "2026-01-15",
   "exercise_name": "squat", "set_number": 3, "reps": 5, "weight_kg": 100},
  {"id": "20260115_str_1_bench_press_1", "activity_id": "20260115_str_1", "date": "2026-01-15",
   "exercise_name": "bench_press", "set_number": 1, "reps": 8, "weight_kg": 70}
]
```

### Food Log
```json
[
  {"date": "2026-01-15", "meal_type": "breakfast", "food_item": "Oatmeal with banana and peanut butter"},
  {"date": "2026-01-15", "meal_type": "breakfast", "food_item": "Coffee"},
  {"date": "2026-01-15", "meal_type": "lunch", "food_item": "Chicken salad with quinoa", "calories": 500}
]
```

### Tasks
```json
[
  {"id": "20260115_task_1", "date": "2026-01-15", "description": "Review PR for auth module", "status": "completed"},
  {"id": "20260115_task_2", "date": "2026-01-15", "description": "Fix the login bug", "status": "completed"},
  {"id": "20260115_task_3", "date": "2026-01-15", "description": "Write tests for extraction", "status": "cancelled"},
  {"id": "20260115_task_4", "date": "2026-01-15", "description": "Call dentist", "status": "pending"}
]
```

## Claude API Prompt Pattern

```python
EXTRACTION_PROMPT = """
Extract structured data from this daily note.

Date from filename: {date}

Note content:
{content}

Extract into these schemas:
{schemas}

Return valid JSON matching the schemas. Use null for missing optional fields.
Only extract data that is explicitly mentioned.
"""
```

## Validation Rules

1. Dates must be valid and match the note's date
2. Activity IDs follow format: `{YYYYMMDD}_{type}_{index}` (e.g., `20260115_str_1`)
3. Exercise log IDs follow format: `{activity_id}_{exercise_name}_{set_number}` (e.g., `20260115_str_1_squat_1`)
4. Exercise names normalized to snake_case (e.g., `bench_press`, not `Bench Press`)
5. Numeric values must be positive
6. Required fields cannot be null
7. Each set is a separate row in exercise_log
