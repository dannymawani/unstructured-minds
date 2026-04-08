# Architecture Overview

Unstructured Minds transforms natural language markdown notes into structured, queryable data via Claude AI + DuckDB/Postgres.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      User's Browser                         │
│         React 19 (Milkdown Editor, Dashboard, Kanban)       │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP / SSE
                ┌────────────▼────────────┐
                │  Nginx (prod) or        │
                │  Vite Dev Server (dev)   │
                └────────────┬────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                     FastAPI Server                           │
│                   (Python 3.12+, async)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ DuckDB /     │  │ LLM Provider │  │ Storage Backend   │ │
│  │ Postgres     │  │ (via LiteLLM │  │ (Filesystem or    │ │
│  │ (data)       │  │  agnostic)   │  │  Postgres)        │ │
│  └──────────────┘  └──────────────┘  └───────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Two Modes

The system runs in one of two modes, determined by environment variables:

| Aspect | Local Mode | Cloud Mode |
|--------|-----------|------------|
| **Trigger** | `STORAGE_MODE=local` (default) | `STORAGE_MODE=postgres` + `DATABASE_URL` |
| **Primary DB** | DuckDB file (`data/unstructured.duckdb`) | Postgres |
| **Analytics DB** | Same DuckDB file | In-memory DuckDB cache |
| **Vault storage** | Local filesystem (`vault/`) | Postgres `vault_files` table |
| **Settings** | JSON files in `data/` | Postgres `user_settings` JSONB |
| **Auth** | Configurable: none / basic / clerk | Configurable: none / basic / clerk |
| **User isolation** | N/A (single user, `user_id = "local"`) | All queries scoped by `user_id` |
| **Required env** | `VAULT_PATH`, `DATA_PATH` | + `DATABASE_URL`, `AUTH_MODE` |

## Project Structure

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
│   └── tests/                  # 25+ test files
├── frontend/                   # React 19 + Vite (port 80/5173)
│   ├── src/
│   │   ├── App.tsx             # Routing, layout, auth gate
│   │   ├── main.tsx            # React root + Clerk provider
│   │   ├── index.css           # Tailwind v4 + theme vars
│   │   ├── components/         # 23 component directories
│   │   ├── hooks/              # 5 custom hooks
│   │   └── lib/                # apiClient, utils
│   ├── nginx.conf              # Production reverse proxy
│   └── nginx/security-headers.conf  # CSP config
├── shared/                     # Git-tracked, shared definitions
│   ├── exercise_definitions.json  # 330+ exercises
│   └── schemas/                # daily_metrics, exercise_log, food_log, daily_tasks
├── data/                       # Gitignored, per-instance
│   ├── unstructured.duckdb     # Active database
│   ├── settings.json           # {theme, show_month_names}
│   ├── training_config.json    # Athlete targets, recovery times
│   └── ai_exercise_cache.json  # Claude-generated exercise aliases
├── vault/                      # Gitignored, markdown notes
│   └── YYYY/MM/YYYY-MM-DD.md  # Daily notes by year/month
├── docker-compose.yml          # Production services
├── docker-compose.dev.yml      # Development services
├── .env                        # Secrets (gitignored)
├── ai_docs/                    # This wiki
└── CLAUDE.md                   # Quick-start routing table
```

## Component Relationships

```
User writes markdown ──► Vault (filesystem/Postgres)
                              │
                              ▼
                     Extraction Pipeline
                     (Claude Haiku 4.5)
                              │
                              ▼
                     DuckDB / Postgres
                     (structured tables)
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              Dashboard   Queries    Tasks
              (analytics) (NL→SQL)  (kanban)
```

## Startup Sequence

**Local mode:**
1. Open DuckDB file → `db` and `analytics_db` point to same connection
2. Init Claude client → load exercise definitions → run exercise normalization

**Cloud mode:**
1. Connect Postgres pool → create schema → init `:memory:` DuckDB
2. Start AnalyticsCacheManager (60s refresh cycle)
3. Init Claude client → load exercise definitions → run exercise normalization

**Middleware stack (order):** RequestLogging → SecurityHeaders → CORS → RateLimiting

## Cross-References

- Database schemas → [04-database-architecture](04-database-architecture.md)
- Backend details → [05-backend](05-backend.md)
- Frontend details → [06-frontend](06-frontend.md)
- Extraction pipeline → [07-data-pipeline](07-data-pipeline.md)
- Auth flow → [08-auth-and-security](08-auth-and-security.md)
- Docker/deploy → [09-infrastructure](09-infrastructure.md)
