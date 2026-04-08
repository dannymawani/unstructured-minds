# Unstructured Minds

Natural language notes → structured, queryable data via Claude + DuckDB/Postgres.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19 + Milkdown |
| Backend | Python >=3.12 + FastAPI |
| Database | DuckDB 1.4 (local) / Neon Postgres (cloud) |
| AI | Claude API (Haiku 4.5 extraction, Sonnet 4.5 queries) |
| Auth | Clerk (required for cloud mode) |
| Deploy | Docker Compose |

## Architecture

For the full system reference (all endpoints, DB schemas, component inventory, env vars, auth flow, Docker config), see the `system-architecture` skill. The sections below are the essentials.

### Two Modes

| Mode | Trigger | Storage |
|------|---------|---------|
| **Local** | `USE_CLOUD=false` | DuckDB file + local filesystem |
| **Cloud** | `USE_CLOUD=true` + `DATABASE_URL` | Postgres + in-memory DuckDB cache |

Env vars: `ANTHROPIC_API_KEY`, `USE_CLOUD`, `DATABASE_URL` (cloud only), `CLERK_SECRET_KEY` + `CLERK_DOMAIN` (cloud only).

Local mode uses `LOCAL_USER_ID = "local"` (hardcoded, not configurable). Cloud mode derives user identity from Clerk JWT — no `DEFAULT_USER_ID` env var.

In cloud mode, per-user settings live in the Postgres `user_settings` table; vault files in `vault_files`.

### Data Layout

```
shared/                       # Git-tracked, shared
├── exercise_definitions.json
└── schemas/*.json

data/                         # Gitignored, per-instance
├── unstructured.duckdb
├── settings.json
├── life_profile.json
├── training_config.json
└── ai_exercise_cache.json
```

### Date Formats

Filenames and CSV dates: `YYYY-MM-DD`. Daily note path: `Daily-Notes/YYYY-MM/YYYY-MM-DD.md`.

### DuckDB

No AUTO_INCREMENT — use `DEFAULT nextval('seq')` or app-generated IDs.

### Dashboard & Analytics Cache

In cloud mode, dashboard endpoints use an in-memory DuckDB (analytics cache) populated from Postgres per-user. The `dashboard.py` module defines a **local `get_db`** that depends on `get_user_id` (auth + cache seeding). This local function **must be defined before all endpoint functions** in the file — Python evaluates `Depends(get_db)` default args at function definition time, so any endpoint defined before the local `get_db` would bind to the imported `dependencies.get_db` (Postgres, no auth, no user isolation).

### Cloud Setup

```bash
cd backend && python3 -m scripts.setup_cloud              # Full setup
cd backend && python3 -m scripts.setup_cloud --drop-first  # Wipe + rebuild
cd backend && python3 -m scripts.setup_cloud --skip-seed   # Schemas only
```

## Testing

Run: `cd backend && pytest` (backend), `cd frontend && npm test` (frontend).

### Auth in Tests

The dev `.env` has Clerk/Postgres credentials, so the real `settings` object has `auth_enabled=True` and `is_cloud_mode=True`. Tests bypass this via an **autouse fixture** in `backend/tests/conftest.py` (`disable_auth`) that:

1. Patches `src.api.dependencies.settings` with `auth_enabled=False`, `is_cloud_mode=False`
2. Overrides `get_user_id` via FastAPI DI to return `LOCAL_USER_ID`

This ensures all dependency functions (`get_storage`, `get_datastore`, `get_user_id`) take the local-mode path. Individual test files that need custom settings patch their own router modules (e.g., `src.api.settings.settings`) on top of this.

See `docs/AUTH.md` for the full auth architecture.

## Workflow

1. **Plan** — Kanban task + plan mode for non-trivial features
2. **Implement** — `feature/{name}` or `fix/{issue}` branch, never commit to `main`
3. **Test** — `pytest` + `npm test` before committing
4. **Review** — `/code-review` before merging
5. **Deploy** — Merge to `main`, verify Docker

### Commit Hygiene

Stage specific files (`git add <files>`), not `git add .`. Check with `git diff --cached --stat`.

## Shell / Environment

- **macOS zsh**: Always quote URLs with single quotes in `curl` commands. Unquoted `?` and `&` trigger zsh globbing errors: `curl -s 'http://localhost:8000/endpoint?param=value'`
- Use `python3` not `python` — only `python3` is on `PATH`.

## Build Pipeline

### Dev-time Type Checking

`vite-plugin-checker` runs TypeScript checking in a worker thread during `npm run dev`. TS errors appear as a browser overlay — no more silent accumulation until `npm run build` fails.

- `npm run dev` — dev server with live type checking overlay
- `npm run typecheck` — standalone TS check (CI/manual use)
- `npm run build` — runs `tsc -b && vite build` (production)

### Docker Build Args

`VITE_CLERK_PUBLISHABLE_KEY` must be a **build arg** (not runtime env) because Vite bakes `VITE_*` variables into the JS bundle at build time. The Dockerfile warns when it's empty (local mode works without it).

### CSP Configuration

Security headers (including CSP) live in `frontend/nginx/security-headers.conf`. This file is `include`d from `nginx.conf` in both the server block and the `location = /index.html` block (nginx doesn't inherit `add_header` from parent when child uses `add_header`). Update CSP in one place only.

### Logo Assets

| File | Purpose | Served from |
|------|---------|-------------|
| `um-icon.svg` | Favicon, PWA icon (brain only) | `frontend/public/` |
| `um-logo.svg` | In-app branding (full logo) | `frontend/public/` |

Source files in `assets/images/` use kebab-case to match web convention.

## CSS/UI

One change at a time. Verify no regressions before the next edit.

## Brand

See `brand-guidelines` skill. Quick ref: Teal `#14b8a6` (primary), Dark `#0f172a`, Light `#f8fafc`, Amber `#f59e0b`, Indigo `#6366f1` (links), Rose `#f43f5e` (errors).

## Keeping Documentation Current

After making **structural changes** to the codebase, update the `system-architecture` skill (`.claude/skills/system-architecture/skill.md`) to reflect the change. Structural changes include:

- Adding/removing/renaming API endpoints or routers
- Adding/removing/renaming frontend components, hooks, or views
- Changing database tables, columns, or indexes
- Adding/removing environment variables or config fields
- Changing Docker services, volumes, or build configuration
- Modifying auth flow, middleware stack, or dependency injection
- Adding/removing dependencies (backend or frontend)
- Changing storage backends or data file formats

**How:** Edit the relevant section in the skill file directly. Keep it concise — match the existing style (tables, short descriptions, no prose). Don't rewrite the whole file; just patch the affected section.

**Skip updates for:** Bug fixes, CSS tweaks, copy changes, test additions, or refactors that don't change the public interface.

---

Skills and agents auto-discovered from `.claude/skills/` and `.claude/agents/`.
