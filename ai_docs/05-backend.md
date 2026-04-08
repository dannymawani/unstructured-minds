# Backend

FastAPI structure, API conventions, Python patterns, dependency injection, and Claude integration.

## Project Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app entry + lifespan
│   ├── config.py            # Settings (pydantic-settings)
│   ├── api/                 # Route modules
│   │   ├── dependencies.py  # DI: get_db, get_storage, get_user_id
│   │   ├── dashboard.py     # Dashboard analytics endpoints
│   │   ├── vault.py         # Vault file CRUD
│   │   ├── extraction.py    # Extract endpoints
│   │   ├── query.py         # NL → SQL query
│   │   ├── tasks.py         # Personal tasks
│   │   ├── kanban.py        # Dev kanban
│   │   ├── settings.py      # User settings
│   │   ├── exercises.py     # Exercise definitions
│   │   └── ...              # calendar, search, tags, export, etc.
│   ├── db/
│   │   ├── connection.py    # DatabaseManager, read_only_execute
│   │   ├── schema.py        # DuckDB schema definitions
│   │   ├── postgres_schema.py # Postgres schema definitions
│   │   └── analytics_cache.py # In-memory DuckDB cache manager
│   ├── extraction/
│   │   ├── pipeline.py      # Extraction orchestration
│   │   └── exercise_matcher.py # Multi-tier exercise matching
│   ├── storage/
│   │   ├── local.py         # LocalFilesystem backend
│   │   └── postgres.py      # PostgresStorage backend
│   ├── claude/
│   │   └── client.py        # Anthropic SDK wrapper
│   ├── middleware/
│   │   ├── clerk_auth.py    # JWT verification
│   │   ├── rate_limit.py    # slowapi
│   │   ├── security_headers.py # CSP, X-Frame-Options
│   │   ├── request_logging.py  # structlog JSON
│   │   └── validation.py    # Path validation
│   ├── onboarding/          # Demo data + lifecycle
│   ├── skills/              # Skill system
│   ├── templates/           # Note templates
│   └── parsing/             # Markdown/tag parsing
├── scripts/                 # setup_cloud, backup, migrations
├── tests/                   # 25+ test files
├── Dockerfile               # python:3.13-slim multi-stage
└── pyproject.toml
```

## Dependency Injection

```python
get_db(request)       → Primary DB (Postgres or DuckDB)
get_analytics_db(req) → Analytics DB (in-memory DuckDB in cloud, same DuckDB in local)
get_storage(req)      → StorageBackend (PostgresStorage or LocalFilesystem)
get_datastore(req)    → DataStore (JSON config access)
get_user_id(req)      → "local" or uuid5(NAMESPACE_URL, clerk_sub)
```

## Settings (`config.py`)

```python
class Settings(BaseSettings):
    vault_path, data_path, host, port, debug, cors_origins
    anthropic_api_key, use_cloud, database_url
    db_pool_min, db_pool_max
    clerk_secret_key, clerk_domain

    @property is_cloud_mode: use_cloud AND database_url is not None
    @property auth_enabled: is_cloud_mode
    @property claude_enabled: anthropic_api_key is not None
```

`LOCAL_USER_ID = "local"` — hardcoded, non-configurable.

## API Endpoints

### Vault Files (`/vault/*`)
- `GET /vault/files` — List files (cached)
- `GET|POST|DELETE|PATCH /vault/file` — CRUD
- `POST /vault/quick-capture` — Append to today's note
- `POST /vault/migrate-daily-notes` — Restructure old paths

### Extraction (`/extract`)
- `POST /extract` — Single file (20/min)
- `POST /extract/batch` — Multiple files (20/min)
- `POST /extract/all` — SSE stream all files

### Dashboard (`/dashboard/*`)
- `GET /dashboard/summary` — KPIs, streak, counts
- `GET /dashboard/weekly-activities` — Activity breakdown
- `GET /dashboard/metrics-trends` — Sleep/energy/mood
- `GET /dashboard/exercise-progress` — Per-exercise stats
- `GET /dashboard/heatmap` — Activity frequency
- `GET /dashboard/predictions` — ML-based recovery/next workout
- `GET /dashboard/nutrition` — Calorie/macro aggregates
- `GET /dashboard/activity-groups` — Grouped activity data
- `POST /dashboard/endurance` — Log endurance activity
- `GET /dashboard/endurance-table` — Endurance session table
- `GET /dashboard/endurance-progress` — Time-series progress
- `GET /dashboard/body-weight` — Body weight trend

### Tasks (`/tasks`)
- `GET|POST /tasks` — List/create (filters: status, date, category)
- `GET|PUT|DELETE /tasks/{id}` — CRUD
- `POST /tasks/bulk-complete` — Batch complete
- `GET /tasks/rollover` — Incomplete tasks for wizard
- `POST /tasks/rollover/commit` — Rollover to new date

### Kanban (`/kanban/*`)
- `GET /kanban/board` — Full board (columns + tasks)
- `POST|PUT|DELETE /kanban/tasks/{id}` — CRUD
- `GET|POST /kanban/tasks/{id}/notes` — Task update notes

### Queries (`/query/*`)
- `POST /query/natural` — NL → SQL → results (30/min)
- `GET /query/suggestion` — Suggested queries (100/min)

### Other
- `/calendar/weekly`, `/calendar/suggest` — Workout calendar
- `/health`, `/health/live`, `/health/ready`, `/health/detailed` — Health probes
- `/search` — Full-text vault search (100/min)
- `/tags`, `/tags/{tag}` — Tag management
- `/settings` (GET/PUT) — Config
- `/export/json`, `/export/csv`, `/import/json` — Data portability (5/min)
- `/skills`, `/skills/{name}/execute` — Custom skill system
- `/schemas` — Custom extraction schemas CRUD
- `/templates` — Template management
- `/exercises` — Exercise definitions
- `/onboarding/status`, `/onboarding/seed`, `/onboarding/clear-demo`, `/onboarding/complete` — Demo data lifecycle
- `/insights` — ML trends/anomalies
- `/note-assist` — Multimodal AI note editing
- `/metrics` — Request metrics

## API Conventions

### HTTP Methods
| Method | Purpose | Success | Errors |
|--------|---------|---------|--------|
| GET | Retrieve | 200 | 404, 400 |
| POST | Create | 201 | 400, 422 |
| PUT | Full update | 200 | 404, 400, 422 |
| PATCH | Partial update | 200 | 404, 400, 422 |
| DELETE | Remove | 204 | 404 |

### Patterns
- Use Pydantic models for all request bodies and responses
- Use `async def` for all route handlers
- Type hints on all function signatures
- Error handling via `HTTPException` with machine-readable codes
- Logging via `structlog` (JSON output)

## Claude AI Integration (`claude/client.py`)

| Method | Model | Purpose |
|--------|-------|---------|
| `extract()` | Haiku 4.5 | Tool-use structured extraction |
| `query()` | Haiku 4.5 | Answer questions from context |
| `note_assist()` | Sonnet 4.5 | Multimodal note editing |
| `populate_daily_note()` | Haiku 4.5 | Fill wizard answers into template |
| `execute_skill()` | Sonnet 4.5 | Custom skill execution |
| `classify_exercises()` | Haiku 4.5 | Exercise name normalization |
| `label_new_exercises()` | Haiku 4.5 | Auto-classify new exercises with muscle groups |

## Storage Backends (`storage/`)

**Protocol:** `read(path) → bytes`, `write(path, content)`, `delete(path)`, `list(prefix)`, `rename(old, new)`, `exists(path)`

- **LocalFilesystem** — reads/writes `VAULT_PATH`, path traversal prevention
- **PostgresStorage** — reads/writes `vault_files` table, user-scoped
- **DataStore** — JSON wrapper over storage for settings/config files

## Database Security (`db/connection.py`)

`DatabaseManager.read_only_execute(sql)` — Wraps AI-generated SQL in `BEGIN TRANSACTION` / `ROLLBACK`. Results materialized into `_MaterializedResult` before rollback. Used by `/query/natural` to ensure writes from prompt injection are always discarded.

## SQL Validation (`api/query.py`)

`validate_sql(sql)` — 4-layer defense:
1. Must start with `SELECT` or `WITH`, no semicolons
2. Keyword deny-list: INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE, EXEC, EXECUTE, ATTACH, DETACH, COPY, LOAD, INSTALL, PRAGMA, CALL, SET, EXPLAIN
3. Function deny-list: `read_csv`, `read_parquet`, `read_json`, `glob`, `http_get`, `system`, `write_csv`, etc.
4. System table blocking: `information_schema`, `duckdb_*`, `pg_*`, `sqlite_*`
5. `duckdb.extract_statements(sql)` — parser ensures exactly 1 valid statement

`ALLOWED_QUERY_TABLES`: `daily_metrics`, `exercise_log`, `activities`, `food_log`, `tasks`
