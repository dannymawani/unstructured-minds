---
name: system-architecture
description: Complete system architecture reference for Unstructured Minds. Covers frontend, backend, database schemas, vault structure, Docker deployment, environment variables, auth flow, and data pipeline. Use when you need to understand how the system works without re-exploring the codebase.
user-invocable: false
---

# System Architecture Reference

Complete technical reference for the Unstructured Minds application. Markdown notes become structured, queryable data via Claude AI + DuckDB/Postgres.

## Project Root Structure

```
unstructured_minds/
├── backend/                    # Python FastAPI (port 8000)
│   ├── src/
│   │   ├── main.py             # App entry + lifespan
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── api/                # 20+ route modules
│   │   ├── db/                 # DuckDB + Postgres + cache
│   │   ├── extraction/         # Claude extraction pipeline
│   │   ├── storage/            # File storage abstraction
│   │   ├── middleware/         # Auth, rate limit, logging, CSP
│   │   ├── claude/             # AI client wrapper
│   │   ├── onboarding/         # Demo data + onboarding lifecycle
│   │   ├── skills/             # Skill system
│   │   ├── templates/          # Note templates
│   │   ├── parsing/            # Markdown/tag parsing
│   │   ├── cache.py            # In-memory caching
│   │   └── logging_config.py   # structlog setup
│   ├── scripts/                # setup_cloud, migrations, backup
│   ├── tests/                  # 25+ test files
│   ├── Dockerfile              # python:3.13-slim multi-stage
│   └── pyproject.toml
├── frontend/                   # React 19 + Vite (port 80/5173)
│   ├── src/
│   │   ├── App.tsx             # Routing, layout, auth gate
│   │   ├── main.tsx            # React root + Clerk provider
│   │   ├── index.css           # Tailwind v4 + theme vars
│   │   ├── components/         # 23 component directories (incl. Onboarding)
│   │   ├── hooks/              # 5 custom hooks
│   │   └── lib/                # apiClient, utils
│   ├── public/                 # um-icon.svg, um-logo.svg, manifest.json
│   ├── nginx.conf              # Production reverse proxy
│   ├── nginx/security-headers.conf  # CSP config
│   ├── Dockerfile              # node:22-alpine + nginx:alpine
│   ├── vite.config.ts          # Proxy, plugins, code splitting
│   └── package.json
├── shared/                     # Git-tracked, shared definitions
│   ├── exercise_definitions.json  # 330+ exercises
│   └── schemas/                # daily_metrics, exercise_log, food_log, daily_tasks
├── data/                       # Gitignored, per-instance
│   ├── unstructured.duckdb     # ~39MB active database
│   ├── settings.json           # {theme, show_month_names}
│   ├── life_profile.json       # User profile (overview, work, training, goals)
│   ├── training_config.json    # Athlete targets, recovery times
│   └── ai_exercise_cache.json  # Claude-generated exercise aliases
├── vault/                      # Gitignored, markdown notes
│   └── YYYY/MM/YYYY-MM-DD.md  # Daily notes by year/month
├── docker-compose.yml          # backend + frontend services
├── .env                        # Secrets (gitignored)
└── CLAUDE.md
```

---

## Environment Variables

### Core

| Variable | Default | Purpose |
|----------|---------|---------|
| `VAULT_PATH` | `./vault` | Markdown notes directory |
| `DATA_PATH` | `./data` | DuckDB, settings, configs |
| `HOST` | `0.0.0.0` | API bind address |
| `PORT` | `8000` | API port |
| `FRONTEND_PORT` | `3000` | Nginx port (Docker) |
| `DEBUG` | `false` | Verbose logging + hot reload |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated |
| `ANTHROPIC_API_KEY` | — | Claude API (sk-ant-...) |

### Cloud Mode (Postgres + Clerk)

| Variable | Required | Purpose |
|----------|----------|---------|
| `USE_CLOUD` | No | `true` enables cloud mode |
| `DATABASE_URL` | Yes* | `postgresql://user:pass@host:port/db` |
| `CLERK_SECRET_KEY` | Yes* | JWT signing key (sk_test_...) |
| `CLERK_DOMAIN` | Yes* | e.g. `more-cobra-67.clerk.accounts.dev` |
| `DB_POOL_MIN` / `DB_POOL_MAX` | No | Connection pool (default 2/10) |

\* Required when `USE_CLOUD=true`

### Frontend (Vite — baked into JS bundle at build time)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Backend URL (default `http://localhost:8000`, Docker: `/api`) |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk public key (must be Docker **build arg**) |
| `VITE_API_PROXY_TARGET` | Vite dev proxy target |

### Settings Class (`backend/src/config.py`)

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

---

## Two Modes: Local vs Cloud

| Aspect | Local | Cloud |
|--------|-------|-------|
| Primary DB | DuckDB file | Postgres (Neon) |
| Analytics DB | Same DuckDB | In-memory DuckDB cache |
| Vault storage | Local filesystem | Postgres `vault_files` table |
| Settings storage | JSON files in `data/` | Postgres `user_settings` JSONB |
| Auth | None (`user_id="local"`) | Clerk JWT → UUID via `uuid5` |
| User isolation | N/A | All queries scoped by `user_id` |
| Required env | `VAULT_PATH`, `DATA_PATH` | + `DATABASE_URL`, `CLERK_*` |

---

## Backend Architecture

### FastAPI App (`main.py`)

**Middleware stack (order):** RequestLogging → SecurityHeaders → CORS → RateLimiting

**Lifespan startup:**
1. Cloud: Connect Postgres pool → create schema → init `:memory:` DuckDB → start AnalyticsCacheManager (60s refresh)
2. Local: Open DuckDB file → both `db` and `analytics_db` point to same connection
3. Common: Init Claude client → load exercise definitions → run exercise normalization

### API Endpoints (All Routers)

**Vault Files** (`/vault/*`):
- `GET /vault/files` — List files (cached)
- `GET|POST|DELETE|PATCH /vault/file` — CRUD
- `POST /vault/quick-capture` — Append to today's note
- `POST /vault/migrate-daily-notes` — Restructure old paths

**Extraction** (`/extract`):
- `POST /extract` — Single file (20/min)
- `POST /extract/batch` — Multiple files (20/min)
- `POST /extract/all` — SSE stream all files

**Dashboard** (`/dashboard/*`):
- `GET /dashboard/summary` — KPIs, streak, counts
- `GET /dashboard/weekly-activities` — Activity breakdown
- `GET /dashboard/metrics-trends` — Sleep/energy/mood
- `GET /dashboard/exercise-progress` — Per-exercise stats
- `GET /dashboard/heatmap` — Activity frequency
- `GET /dashboard/predictions` — ML-based recovery/next workout
- `GET /dashboard/nutrition` — Calorie/macro aggregates
- `GET /dashboard/activity-groups` — Grouped activity data
- `POST /dashboard/endurance` — Log endurance activity (running/cycling/swimming)
- `GET /dashboard/endurance-table` — Endurance session table with pace/speed
- `GET /dashboard/endurance-progress` — Time-series progress for a sport
- `GET /dashboard/body-weight` — Body weight trend with period change

**Tasks** (`/tasks`):
- `GET|POST /tasks` — List/create (filters: status, date, category)
- `GET|PUT|DELETE /tasks/{id}` — CRUD
- `POST /tasks/bulk-complete` — Batch complete
- `GET /tasks/rollover` — Incomplete tasks for wizard
- `POST /tasks/rollover/commit` — Rollover to new date

**Kanban** (`/kanban/*`):
- `GET /kanban/board` — Full board (columns + tasks)
- `POST|PUT|DELETE /kanban/tasks/{id}` — CRUD
- `GET|POST /kanban/tasks/{id}/notes` — Task update notes

**Queries** (`/query/*`):
- `POST /query/natural` — NL → SQL → results (30/min). Defense-in-depth: system prompt separation, `validate_sql()` (keyword deny-list + function deny-list + system table blocking + DuckDB parser), `read_only_execute()` (BEGIN/ROLLBACK), auto LIMIT 100
- `GET /query/suggestion` — Suggested queries (100/min)

**Other:**
- `/calendar/weekly`, `/calendar/suggest` — Workout calendar
- `/health`, `/health/live`, `/health/ready`, `/health/detailed` — Health probes
- `/search` — Full-text vault search (100/min)
- `/tags`, `/tags/{tag}` — Tag management
- `/settings` (GET/PUT), `/profile` (GET/PUT) — Config
- `/export/json`, `/export/csv`, `/import/json` — Data portability (5/min)
- `/skills`, `/skills/{name}/execute` — Custom skill system
- `/schemas` — Custom extraction schemas CRUD
- `/templates` — Template management
- `/exercises` — Exercise definitions
- `/onboarding/status` (GET), `/onboarding/seed` (POST), `/onboarding/clear-demo` (POST), `/onboarding/complete` (POST) — Demo data lifecycle
- `/insights` — ML trends/anomalies
- `/note-assist` — Multimodal AI note editing
- `/metrics` — Request metrics

### Dependency Injection (`api/dependencies.py`)

```
get_db(request)       → Primary DB (Postgres or DuckDB)
get_analytics_db(req) → Analytics DB (in-memory DuckDB in cloud, same DuckDB in local)
get_storage(req)      → StorageBackend (PostgresStorage or LocalFilesystem)
get_datastore(req)    → DataStore (JSON config access)
get_user_id(req)      → "local" or uuid5(NAMESPACE_URL, clerk_sub)
```

**CRITICAL:** `dashboard.py` defines a **local `get_db`** that depends on `get_user_id` (auth + cache seeding). This local function **must be defined before all endpoint functions** — Python evaluates `Depends()` defaults at function definition time.

### Database Security (`db/connection.py`)

`DatabaseManager.read_only_execute(sql)` — Wraps AI-generated SQL in `BEGIN TRANSACTION` / `ROLLBACK`. Results are materialized into `_MaterializedResult` before rollback. Used exclusively by `/query/natural` to ensure writes from prompt injection are always discarded.

### SQL Validation (`api/query.py`)

`validate_sql(sql)` — 4-layer defense:
1. Must start with `SELECT` or `WITH`, no semicolons (multi-statement)
2. Keyword deny-list: INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE, EXEC, EXECUTE, ATTACH, DETACH, COPY, LOAD, INSTALL, PRAGMA, CALL, SET, EXPLAIN
3. Function deny-list (`DANGEROUS_FUNCTIONS`): `read_csv`, `read_parquet`, `read_json`, `glob`, `http_get`, `system`, `write_csv`, `write_parquet`, etc.
4. System table blocking (`BLOCKED_TABLE_PATTERNS`): `information_schema`, `duckdb_*`, `pg_*`, `sqlite_*`
5. `duckdb.extract_statements(sql)` — parser ensures exactly 1 valid statement

`ALLOWED_QUERY_TABLES`: `daily_metrics`, `exercise_log`, `activities`, `food_log`, `tasks`

SQL generation uses `system` parameter (not user message) with explicit anti-injection rules. Claude returns `INVALID_QUERY` for non-data questions.

### Storage Backends (`storage/`)

**Protocol:** `read(path) → bytes`, `write(path, content)`, `delete(path)`, `list(prefix)`, `rename(old, new)`, `exists(path)`

- **LocalFilesystem** — reads/writes `VAULT_PATH`, path traversal prevention
- **PostgresStorage** — reads/writes `vault_files` table, user-scoped
- **DataStore** — JSON wrapper over storage for settings/profile/config files

### Claude AI Integration (`claude/client.py`)

| Method | Model | Purpose |
|--------|-------|---------|
| `extract()` | Haiku 4.5 | Tool-use structured extraction |
| `query()` | Haiku 4.5 | Answer questions from context |
| `note_assist()` | Sonnet 4.5 | Multimodal note editing |
| `populate_daily_note()` | Haiku 4.5 | Fill wizard answers into template |
| `execute_skill()` | Sonnet 4.5 | Custom skill execution |
| `classify_exercises()` | Haiku 4.5 | Exercise name normalization |

**Extraction flow:** File written → hash check (skip if unchanged) → load schema → Claude tool-use call → parse response → upsert into DB → log to `extraction_log`

### Middleware

- **Clerk auth** (`clerk_auth.py`): JWKS fetch (1h cache), RSA key cache by KID, retry on rotation
- **Rate limiting** (`rate_limit.py`): slowapi, per-endpoint limits
- **Validation** (`validation.py`): Max 255 char paths, no `..` traversal
- **Security headers** (`security_headers.py`): CSP, X-Frame-Options, nosniff
- **Request logging** (`request_logging.py`): structlog JSON, excludes /health

---

## Frontend Architecture

### Tech Stack

React 19 + Vite 7 + TypeScript 5.9 (strict) + Tailwind v4 + Milkdown 7 + Clerk + lucide-react

### Views (Lazy-loaded)

1. **Editor** (`/`, `/editor`) — Milkdown markdown editor + sidebar + chat
2. **Dashboard** (`/dashboard`) — Configurable analytics widgets
3. **Kanban** (`/kanban`) — 4-column personal task board (Backlog → In Progress → Done → Cancelled)
4. **Calendar** (`/calendar`) — Monthly calendar with daily note indicators
5. **Profile** (`/profile`) — Life profile editor (overview, personal, work, training, goals)

### Component Inventory (22 directories)

**Layout:** Drawer (mobile slide-out), MobileNav (bottom tabs)
**Files:** FileTree (virtualized, nested), FileTreeItem (memoized)
**Editor:** MarkdownEditor (Milkdown), EditorToolbar (formatting buttons), EditorPlugins (slash menu, code block exit)
**Chat:** ChatPanel (AI assistant), ChatMessage (with query results table)
**Dashboard:** Dashboard, DashboardSummary, WeeklyActivityChart, MetricsTrends, ExerciseTable, ActivityHeatmap, SleepTrends, MoodCorrelation, NutritionTile, ExerciseProgress, EnduranceLog, EnduranceProgress, InsightsCard, WidgetConfig
**Tasks:** PersonalKanban, PersonalTaskCard (draggable), PersonalTaskModal
**Modals:** CommandPalette (Cmd+K), SearchModal, QuickCapture, TemplatePicker, SettingsPanel, DailyNoteWizard
**Profile:** LifeProfile, OverviewSection, PersonalSection, WorkSection, TrainingSection, GoalsSection, ProgressReviews
**Calendar:** CalendarView
**UI:** Button (CVA variants), SchemaManager

### State Management (Hooks, No Global Store)

- **useUIState()** — Modal visibility, sidebar state, mobile drawers, wizard state
- **useFileManager()** — File selection, content, autosave (60s), dirty tracking, save state
- **useTheme()** — Light/dark mode (localStorage persisted, `.dark` class on root)
- **useMobile()** — Responsive breakpoints: mobile (<640), tablet (640-1024), desktop (>=1024)
- **useKeyboardShortcuts()** — Global keyboard listener

### Keyboard Shortcuts

```
Cmd+S              → Save
Cmd+K              → Command palette
Cmd+B              → Toggle sidebar
Cmd+D              → Today's daily note
Cmd+Shift+F        → Search
Cmd+Shift+N        → Quick capture
Cmd+T              → New from template
```

### API Client (`lib/apiClient.ts`)

- Base URL: `VITE_API_URL` (default `http://localhost:8000`, Docker: `/api`)
- **Global fetch interceptor** patches `window.fetch` to inject `Authorization: Bearer` header
- Token gate: Promise blocks requests until Clerk initializes (resolves immediately if no Clerk)
- Methods: `api.get<T>()`, `api.post<T>()`, `api.put<T>()`, `api.patch<T>()`, `api.delete<T>()`, `api.raw()` (SSE)

### Milkdown Editor

Plugins: commonmark, gfm (tables, strikethrough), history (undo/redo), listener (change events), slash menu (`/`), custom codeBlockExitPlugin (Mod-Enter)
Toolbar: Bold, Italic, Strikethrough, Code, H1-H3, Lists, Quote, Code Block, Divider, Table (interactive grid picker)
Max-width: 52rem, Font: Inter

### Vite Config

- React plugin + Tailwind v4 plugin + vite-plugin-checker (TS errors in browser overlay)
- Path alias: `@/` → `./src/`
- API proxy: `/api` → backend
- Code splitting: vendor-react, vendor-milkdown, vendor-icons
- Bundle analyzer: `npm run analyze`

### CSS/Theming

- Tailwind v4 via `@tailwindcss/vite` (no postcss)
- Dark (default) / Light themes via CSS custom properties
- Dark BG: `#0f172a`, Light BG: `#f3f4f6`, Accent: `#14b8a6` (teal)
- Mobile-first responsive, 44px touch targets, safe area insets

### Docker (Frontend)

- Build: `node:22-alpine` → `npm ci && npm run build`
- Runtime: `nginx:alpine` serving `/usr/share/nginx/html`
- Nginx: gzip, SPA routing, `/api/*` → `http://backend:8000/`, long-lived `/assets/` cache, CSP headers
- Healthcheck: `wget --spider http://localhost:80/`

### PWA

`manifest.json`: standalone display, `#0f172a` bg, `#14b8a6` theme, `um-icon.svg` icon

---

## Database Schemas

### DuckDB Tables (Local Mode & Analytics Cache)

**activities** — `id` (PK), `date`, `activity_type`, `duration_minutes`, `notes`, `source_file`, `extracted_at`

**exercise_log** — `id` (PK), `activity_id` (FK), `date`, `exercise_name`, `weight_kg`, `reps`, `set_number`, `duration_minutes`, `distance_km`, `notes`, `source_file`, `extracted_at`

**daily_metrics** — `date` (PK), `sleep_hours`, `sleep_quality`, `energy`, `mood`, `stress`, `weight_kg`, `notes`, `source_file`, `extracted_at`

**food_log** — `id` (PK), `date`, `meal_type`, `time`, `description`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `notes`, `source_file`, `extracted_at`

**tasks** — `id` (PK), `date`, `description`, `status` (backlog/in_progress/done/cancelled), `completed_at`, `category`, `priority`, `source_file`, `deadline`, `notes`, `extracted_at`

**kanban_tasks** — `id` (PK), `title`, `phase`, `priority`, `status` (not_started/in_progress/done/blocked), `branch`, `depends_on`, `description`, `content`, `deadline`, `created_at`, `completed_at`

**kanban_task_updates** — `id` (SERIAL PK), `task_id`, `note`, `created_at`

**progress_reviews** — `id` (PK), `period_start`, `period_end`, `key_wins` (TEXT[]), `challenges` (TEXT[]), `work_highlights`, `training_summary`, `personal_wins` (TEXT[]), `health_metrics` (JSON), `goal_progress` (JSON), `focus_next` (TEXT[]), `created_at`, `updated_at`

**community_exercises** — `exercise_key` (PK), `display_name`, `aliases`, `muscle_groups`, `category`, `recovery_hours`, `created_at`

**file_index** — `path` (PK), `filename`, `extension`, `size_bytes`, `modified_at`, `content_hash`

**extraction_log** — `id` (SERIAL), `file_path`, `file_hash`, `extracted_at`, `success`, `error_message`

**20+ indexes** on date, status, path, composite keys.

### Postgres Extensions (Cloud Mode)

All tables add `user_id UUID NOT NULL`. Primary keys become composite: `(user_id, id)` or `(user_id, date)`.

**Additional cloud-only tables:**

**vault_files** — `path`, `user_id` (UUID), `content` (TEXT), `size_bytes`, `content_hash`, `created_at`, `updated_at`. PK: `(user_id, path)`

**user_settings** — `user_id` (UUID), `key` (VARCHAR), `value` (JSONB), `updated_at`. PK: `(user_id, key)`. Keys: `settings`, `life_profile`, `training_config`, `ai_exercise_cache`

**custom_extractions** — `id`, `user_id`, `schema_name`, `date`, `data` (JSONB), `source_file`, `extracted_at`

### Shared Schemas (`shared/schemas/`)

- `daily_metrics.json` — weight, sleep/energy/nutrition/mood ratings (1-10)
- `exercise_log.json` — activity_type (strength/bjj/cardio/running/cycling/swimming/yoga/walk/recovery/other), exercise_name, weight/reps/sets/distance
- `food_log.json` — meal (breakfast/lunch/dinner/snack), food, calories, protein
- `daily_tasks.json` — task, status (pending/completed/cancelled/rolled_over), category, priority

### Exercise Definitions (`shared/exercise_definitions.json`)

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

---

## Analytics Cache (Cloud Mode)

**Purpose:** Fast in-memory DuckDB for dashboard queries, seeded from Postgres.

**Tables cached:** activities, exercise_log, daily_metrics, food_log, tasks, extraction_log, kanban_tasks, kanban_task_updates, progress_reviews

**Lifecycle:**
1. App starts → create `:memory:` DuckDB + AnalyticsCacheManager
2. First authenticated request → `cache_mgr.refresh(user_id)` pulls user data from Postgres
3. Background thread → refresh every 60s
4. Dashboard endpoints → query in-memory DuckDB (fast)

---

## Auth Flow (Cloud Mode)

```
Frontend                     Backend
   │                            │
   ├─ Clerk getToken() ────────►│ Authorization: Bearer <JWT>
   │                            │
   │                            ├─ verify_clerk_token()
   │                            │   ├─ Extract JWT, get kid
   │                            │   ├─ Fetch JWKS (cached 1h)
   │                            │   ├─ Verify RSA signature
   │                            │   └─ Decode payload
   │                            │
   │                            ├─ get_user_id()
   │                            │   ├─ payload["sub"] (Clerk ID)
   │                            │   ├─ uuid5(NAMESPACE_URL, sub)
   │                            │   └─ Seed analytics cache if first request
   │                            │
   │                            ├─ get_storage(user_id)
   │                            │   └─ PostgresStorage scoped by user_id
   │                            │
   │                            └─ All DB queries include WHERE user_id = ?
```

---

## Vault & Daily Notes

**Path pattern:** `vault/YYYY/MM/YYYY-MM-DD.md`

**Daily note template sections:**
- `## Adhoc Notes` — Freeform bullets
- `## Today's Focus` — Top 3-4 checkbox items
- `## Carried Forward` — Rolled-over tasks with deadline status
- `## Work` — Work checkbox items
- `## Personal` — Personal checkbox items
- `## Training & Health` → `### Workout` (type, duration, highlights) + `### Energy & Recovery` (sleep/energy/mood ratings)
- `## Wins Today` — Accomplishments
- `## Tomorrow's Priorities` — Numbered items

**Frontmatter:** `date`, `type: daily-note`, `tags: [daily, journal]`

---

## Docker Compose

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ${VAULT_PATH:-./vault}:/app/vault:rw
      - ${DATA_PATH:-./data}:/app/data:rw
    environment:
      ANTHROPIC_API_KEY, USE_CLOUD, DATABASE_URL, VAULT_PATH=/app/vault,
      DATA_PATH=/app/data, HOST=0.0.0.0, PORT=8000, DEBUG,
      CLERK_SECRET_KEY, CLERK_DOMAIN
    healthcheck: curl -f http://localhost:8000/health (30s)
    networks: [app-network]

  frontend:
    build:
      context: ./frontend
      args: [VITE_CLERK_PUBLISHABLE_KEY]
    ports: ["${FRONTEND_PORT:-3000}:80"]
    depends_on: backend (service_healthy)
    healthcheck: wget --spider http://localhost:80/nginx-health (30s)
    networks: [app-network]
```

---

## Data Config Files (`data/`)

**settings.json:** `{theme, show_month_names}`

**life_profile.json:** `{overview: {name, role, company, location}, work: {skills, projects, colleagues}, personal: {family, friends, interests}, training: {disciplines, current_lifts}, goals: [{id, status, category, description, progress}]}`

**training_config.json:** `{athlete: {age, height_cm, weight_kg, bjj_days}, targets: {sleep_hours, daily_calories, daily_protein_g, strength/bjj/cardio sessions_per_week}, recovery: {bjj/large/medium/small muscles hours}, core_lifts, preferences: {working_sets_range, deload_week_frequency}}`

**ai_exercise_cache.json:** Maps raw exercise names → canonical names (e.g. `"4k run" → "Running"`)

---

## Dependencies

### Backend (pyproject.toml)

**Runtime:** fastapi >=0.115, uvicorn[standard], anthropic >=0.40, duckdb >=1.0, pydantic >=2.0, pydantic-settings, python-dotenv, aiofiles >=24.0, sse-starlette >=2.0, structlog >=24.0, slowapi >=0.1.9, psycopg[binary] >=3.2, psycopg-pool, PyJWT[crypto] >=2.9, httpx >=0.27, python-multipart

**Dev:** pytest >=8.0, pytest-asyncio, pytest-cov, ruff >=0.5, mypy >=1.10

### Frontend (package.json)

**Runtime:** react@19, react-dom@19, react-router@7, @milkdown/kit@7, @milkdown/react@7, @clerk/clerk-react@5, tailwindcss@4, @tailwindcss/vite@4, @dnd-kit/core@6, @dnd-kit/sortable@10, @tanstack/react-virtual@3, lucide-react, clsx, tailwind-merge, class-variance-authority, @radix-ui/react-slot

**Dev:** typescript@5.9, vite@7, @vitejs/plugin-react@5, vite-plugin-checker, vitest@4, @testing-library/react@16, jsdom@27, rollup-plugin-visualizer

---

## Testing

**Backend:** `cd backend && pytest` — autouse fixture in `conftest.py` patches `settings` (auth_enabled=False, is_cloud_mode=False) and overrides `get_user_id` to return `LOCAL_USER_ID`

**Frontend:** `cd frontend && npm test` — Vitest + @testing-library/react + jsdom

---

## Scripts

| Script | Command | Purpose |
|--------|---------|---------|
| `setup_cloud` | `python3 -m scripts.setup_cloud` | Create Postgres schema + seed vault + migrate DuckDB |
| `setup_cloud --drop-first` | | Wipe + rebuild |
| `setup_cloud --skip-seed` | | Schemas only |
| `backup_to_local` | `python3 -m scripts.backup_to_local` | Postgres → local DuckDB backup |
| `migrate_duckdb_to_postgres` | | DuckDB → Postgres migration |
| `migrate_user_id` | | Normalize user IDs to UUIDs |
| `seed_vault` | | Insert filesystem files into vault_files table |

---

## Key Architectural Decisions

1. **No AUTO_INCREMENT in DuckDB** — Use `DEFAULT nextval('seq')` or app-generated IDs
2. **Prepared statements disabled** in Postgres for PgBouncer/Supavisor compatibility
3. **dashboard.py local `get_db` before endpoints** — Python evaluates `Depends()` at definition time
4. **Global fetch interceptor** — Patches `window.fetch` for auth, not per-request
5. **uuid5 for user IDs** — Deterministic Clerk sub → UUID mapping
6. **CSP in one file** — `nginx/security-headers.conf` included in both server and location blocks
7. **VITE_CLERK_PUBLISHABLE_KEY as build arg** — Vite bakes `VITE_*` at build time
8. **Defense-in-depth for AI-generated SQL** — 4 layers: system prompt separation, `validate_sql()` deny-lists + DuckDB parser, `read_only_execute()` BEGIN/ROLLBACK, auto LIMIT 100
