# Database Architecture

DuckDB + Postgres schemas, two-mode data layer, analytics cache, and sequences.

## Two-Mode Data Layer

| Aspect | Local Mode | Cloud Mode |
|--------|-----------|------------|
| Primary DB | DuckDB file (`data/unstructured.duckdb`) | Postgres (Neon) |
| Analytics DB | Same DuckDB connection | In-memory DuckDB cache |
| User scoping | N/A (`user_id = "local"`) | All tables add `user_id UUID NOT NULL` |
| Primary keys | Single column | Composite: `(user_id, id)` or `(user_id, date)` |

## DuckDB Notes

- **No AUTO_INCREMENT** — use `DEFAULT nextval('seq')` or app-generated IDs
- Prepared statements disabled in Postgres for PgBouncer/Supavisor compatibility

## Table Schemas

### activities
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR PK | Format: `{YYYYMMDD}_{type}_{index}` (e.g., `20260115_str_1`) |
| `date` | DATE | |
| `activity_type` | VARCHAR | str, bjj, run, rec, cardio, yoga, walk, etc. |
| `duration_minutes` | INTEGER | |
| `notes` | VARCHAR | |
| `source_file` | VARCHAR | |
| `extracted_at` | TIMESTAMP | |

### exercise_log
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR PK | Format: `{activity_id}_{exercise_name}_{set_number}` |
| `activity_id` | VARCHAR FK | References `activities.id` |
| `date` | DATE | |
| `exercise_name` | VARCHAR | snake_case normalized |
| `weight_kg` | DECIMAL | |
| `reps` | INTEGER | |
| `set_number` | INTEGER | Each set is a separate row |
| `duration_minutes` | INTEGER | For timed exercises |
| `distance_km` | DECIMAL | For cardio |
| `notes` | VARCHAR | |
| `source_file` | VARCHAR | |
| `extracted_at` | TIMESTAMP | |

### daily_metrics
| Column | Type | Notes |
|--------|------|-------|
| `date` | DATE PK | |
| `sleep_hours` | DECIMAL | |
| `sleep_quality` | INTEGER | 1-10 scale |
| `energy` | INTEGER | 1-10 scale |
| `mood` | INTEGER | 1-10 scale |
| `stress` | INTEGER | 1-10 scale |
| `weight_kg` | DECIMAL | |
| `notes` | VARCHAR | |
| `source_file` | VARCHAR | |
| `extracted_at` | TIMESTAMP | |

### food_log
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR PK | |
| `date` | DATE | |
| `meal_type` | VARCHAR | breakfast, lunch, dinner, snack |
| `time` | VARCHAR | Optional |
| `description` | VARCHAR | |
| `calories` | NUMERIC | |
| `protein_g` | NUMERIC | |
| `carbs_g` | NUMERIC | |
| `fat_g` | NUMERIC | |
| `notes` | VARCHAR | |
| `source_file` | VARCHAR | |
| `extracted_at` | TIMESTAMP | |

### tasks
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR PK | Format: `{YYYYMMDD}_{8-char-hex}` |
| `date` | DATE | |
| `description` | VARCHAR | |
| `status` | VARCHAR | backlog, in_progress, done, cancelled |
| `completed_at` | TIMESTAMP | Auto-set when done/cancelled |
| `category` | VARCHAR | work, personal, training, other |
| `priority` | INTEGER | 1-3 |
| `source_file` | VARCHAR | |
| `deadline` | DATE | Optional |
| `notes` | VARCHAR | |
| `extracted_at` | TIMESTAMP | |

**Status migrations on startup:** `pending`/`todo` → `backlog`, `completed` → `done`, `rolled_over` → `in_progress`

### kanban_tasks
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR PK | Derived from title (lowercase, hyphens, max 60 chars) |
| `title` | VARCHAR | |
| `phase` | VARCHAR | Development phase (optional) |
| `priority` | VARCHAR | Priority label |
| `status` | VARCHAR | not_started, in_progress, done, blocked |
| `branch` | VARCHAR | Git branch name |
| `depends_on` | VARCHAR | ID of blocking task |
| `description` | VARCHAR | |
| `content` | TEXT | Extended content / acceptance criteria |
| `deadline` | DATE | |
| `created_at` | TIMESTAMP | |
| `completed_at` | TIMESTAMP | |

### kanban_task_updates
| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PK | Auto-incrementing |
| `task_id` | VARCHAR FK | References `kanban_tasks.id`, cascade delete |
| `note` | TEXT | |
| `created_at` | TIMESTAMP | |

### progress_reviews
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR PK | |
| `period_start` | DATE | |
| `period_end` | DATE | |
| `key_wins` | TEXT[] | |
| `challenges` | TEXT[] | |
| `work_highlights` | TEXT | |
| `training_summary` | TEXT | |
| `personal_wins` | TEXT[] | |
| `health_metrics` | JSON | |
| `goal_progress` | JSON | |
| `focus_next` | TEXT[] | |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

### community_exercises
| Column | Type | Notes |
|--------|------|-------|
| `exercise_key` | VARCHAR PK | |
| `display_name` | VARCHAR | |
| `aliases` | VARCHAR/JSONB | JSON string (DuckDB) / JSONB (Postgres) |
| `muscle_groups` | VARCHAR/JSONB | JSON string (DuckDB) / JSONB (Postgres) |
| `category` | VARCHAR | |
| `recovery_hours` | INTEGER | |
| `created_at` | TIMESTAMP | |

### file_index
| Column | Type | Notes |
|--------|------|-------|
| `path` | VARCHAR PK | |
| `filename` | VARCHAR | |
| `extension` | VARCHAR | |
| `size_bytes` | INTEGER | |
| `modified_at` | TIMESTAMP | |
| `content_hash` | VARCHAR | |

### extraction_log
| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL | |
| `file_path` | VARCHAR | |
| `file_hash` | VARCHAR | |
| `extracted_at` | TIMESTAMP | |
| `success` | BOOLEAN | |
| `error_message` | VARCHAR | |

20+ indexes on date, status, path, and composite keys.

## Cloud-Only Tables

### vault_files
| Column | Type | Notes |
|--------|------|-------|
| `path` | VARCHAR | |
| `user_id` | UUID | |
| `content` | TEXT | |
| `size_bytes` | INTEGER | |
| `content_hash` | VARCHAR | |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

PK: `(user_id, path)`

### user_settings
| Column | Type | Notes |
|--------|------|-------|
| `user_id` | UUID | |
| `key` | VARCHAR | `settings`, `training_config`, `ai_exercise_cache` |
| `value` | JSONB | |
| `updated_at` | TIMESTAMP | |

PK: `(user_id, key)`

### custom_extractions
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR | |
| `user_id` | UUID | |
| `schema_name` | VARCHAR | |
| `date` | DATE | |
| `data` | JSONB | |
| `source_file` | VARCHAR | |
| `extracted_at` | TIMESTAMP | |

## Analytics Cache (Cloud Mode)

Fast in-memory DuckDB for dashboard queries, seeded from Postgres.

**Tables cached:** activities, exercise_log, daily_metrics, food_log, tasks, extraction_log, kanban_tasks, kanban_task_updates, progress_reviews

**Lifecycle:**
1. App starts → create `:memory:` DuckDB + AnalyticsCacheManager
2. First authenticated request → `cache_mgr.refresh(user_id)` pulls user data from Postgres
3. Background thread → refresh every 60s
4. Dashboard endpoints → query in-memory DuckDB (fast)

**CRITICAL:** `dashboard.py` defines a **local `get_db`** that depends on `get_user_id` (auth + cache seeding). This local function **must be defined before all endpoint functions** in the file — Python evaluates `Depends()` defaults at function definition time, so any endpoint defined before the local `get_db` would bind to the imported `dependencies.get_db` (Postgres, no auth, no user isolation).

## Shared Schemas (`shared/schemas/`)

JSON schemas used by the extraction pipeline:

- `daily_metrics.json` — weight, sleep/energy/nutrition/mood ratings (1-10)
- `exercise_log.json` — activity_type (strength/bjj/cardio/running/cycling/swimming/yoga/walk/recovery/other), exercise_name, weight/reps/sets/distance
- `food_log.json` — meal (breakfast/lunch/dinner/snack), food, calories, protein
- `daily_tasks.json` — task, status (pending/completed/cancelled/rolled_over), category, priority

## Exercise Definitions (`shared/exercise_definitions.json`)

330+ exercises. Structure per entry:
```json
{
  "deadlift": {
    "display": "Deadlift",
    "aliases": ["dødløft", "deadlifts"],
    "muscle_groups": ["back", "hamstrings", "glutes", "core", "lower_back"],
    "category": "compound",
    "recovery_hours": 72
  }
}
```

## Date Formats

- Filenames and CSV dates: `YYYY-MM-DD`
- Daily note path: `Daily-Notes/YYYY-MM/YYYY-MM-DD.md`
- Vault storage: `vault/YYYY/MM/YYYY-MM-DD.md`

## Data Config Files (`data/`)

| File | Contents |
|------|----------|
| `settings.json` | `{theme, show_month_names}` |
| `training_config.json` | Athlete profile, targets, recovery times, core lifts, preferences |
| `ai_exercise_cache.json` | Raw exercise name → canonical name mapping (e.g., `"4k run" → "Running"`) |
