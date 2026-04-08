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

## Two Modes

| Mode | Trigger | Storage |
|------|---------|---------|
| **Local** | `USE_CLOUD=false` | DuckDB file + local filesystem |
| **Cloud** | `USE_CLOUD=true` + `DATABASE_URL` | Postgres + in-memory DuckDB cache |

Env vars: `ANTHROPIC_API_KEY`, `USE_CLOUD`, `DATABASE_URL` (cloud only), `CLERK_SECRET_KEY` + `CLERK_DOMAIN` (cloud only).

## Deep Documentation → `ai_docs/`

For detailed reference beyond these essentials, see the **`ai_docs/`** wiki. Start with `ai_docs/00-index.md` or use the **librarian agent** to look up specific topics.

| Doc | Covers |
|-----|--------|
| `01-architecture-overview` | System design, data flow, project structure |
| `02-technology-stack` | All technologies, versions, why chosen |
| `03-development-workflow` | Branching, commits, PRs, testing process |
| `04-database-architecture` | All table schemas, two-mode data layer, analytics cache |
| `05-backend` | FastAPI endpoints, DI, Python patterns, Claude integration |
| `06-frontend` | React components, state, Milkdown, build pipeline |
| `07-data-pipeline` | Extraction flow, exercise matching, AI classification |
| `08-auth-and-security` | Clerk auth, JWT, CSP, SQL validation, test auth bypass |
| `09-infrastructure` | Docker, env vars, cloud setup, backup, LAN access |
| `10-decisions-log` | Architectural decisions (ADR, append-only) |

## Testing

Run: `cd backend && pytest` (backend), `cd frontend && npm test` (frontend).

Auth bypass in tests: autouse fixture in `conftest.py` patches `settings` and overrides `get_user_id`. See `ai_docs/08-auth-and-security.md` for details.

## Workflow

1. **Plan** — Kanban task + plan mode for non-trivial features
2. **Implement** — `feature/{name}` or `fix/{issue}` branch, never commit to `main`
3. **Test** — `pytest` + `npm test` before committing
4. **Review** — `/code-review` before merging
5. **Deploy** — Merge to `main`, verify Docker

### Commit Hygiene

Stage specific files (`git add <files>`), not `git add .`. Check with `git diff --cached --stat`.

## Shell / Environment

- **macOS zsh**: Always quote URLs with single quotes in `curl` commands. Unquoted `?` and `&` trigger zsh globbing errors.
- Use `python3` not `python` — only `python3` is on `PATH`.

## Build Pipeline

- `npm run dev` — dev server with live type checking overlay
- `npm run typecheck` — standalone TS check (CI/manual)
- `npm run build` — `tsc -b && vite build` (production)
- `VITE_CLERK_PUBLISHABLE_KEY` must be a **build arg** (Vite bakes `VITE_*` at build time)

## CSS/UI

One change at a time. Verify no regressions before the next edit.

## Keeping Documentation Current

After **structural changes**, update the relevant `ai_docs/` file and the `system-architecture` skill. See `ai_docs/03-development-workflow.md` for what counts as structural.

For significant architectural decisions, append to `ai_docs/10-decisions-log.md`.

## Ideas Bank → `ideas/`

Future plans and feature ideas live in `ideas/`. Each idea gets its own `.md` file with status, rationale, and phased implementation notes.

| Idea | Summary |
|------|---------|
| `multimodal-content-support` | Image paste, PDF upload, vision-based extraction, binary storage |

---

Skills and agents auto-discovered from `.claude/skills/` and `.claude/agents/`.
