# Unstructured Minds — Video CV Demo

## What This Project Is

**Unstructured Minds** turns natural language notes into structured, queryable data. Write freely in markdown — the system extracts structured information using Claude AI and stores it in DuckDB/Postgres for analysis and dashboards.

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript, Milkdown (WYSIWYG markdown editor) |
| Backend | Python 3.12+, FastAPI |
| Database | DuckDB (local) / Supabase Postgres (cloud) |
| AI | Claude API — Haiku for extraction, Sonnet for queries |
| Auth | Clerk (JWT-based, cloud mode) |
| Infra | Docker Compose, Cloudflare Pages (landing), GitHub Actions CI/CD |

## Architecture Highlights

- **Dual-mode deployment**: local-first with DuckDB file storage, or cloud with Postgres + in-memory DuckDB analytics cache
- **Per-user data isolation** in cloud mode via Clerk JWT identity
- **AI extraction pipeline**: markdown notes are parsed by Claude to populate structured tables automatically
- **Dashboard with analytics cache**: cloud mode seeds an in-memory DuckDB from Postgres per-user for fast dashboard queries
- **CSP-hardened Nginx** frontend serving with security headers

## What I Built & Why

1. **Full-stack from scratch** — no boilerplate generators, every layer hand-written
2. **Editor UX** — WYSIWYG Milkdown editor with template discoverability, autosave, raw markdown toggle
3. **Data pipeline** — natural language → Claude extraction → DuckDB/Postgres → queryable dashboards
4. **Auth system** — Clerk integration with JWKS caching, key rotation handling, and test-mode bypass
5. **Cloud deployment** — Docker Compose orchestration, Cloudflare Pages landing page, GitHub Actions workflows
6. **Developer tooling** — dev-time TypeScript checking via vite-plugin-checker, pytest + vitest test suites

## Demo Flow

1. **Start the stack** — `docker compose -f docker-compose.dev.yml up`
2. **Create a note** — open the editor, write a daily note or use a template
3. **Watch extraction** — Claude parses the note and populates structured tables
4. **Query the data** — dashboard widgets show analytics from extracted data
5. **Show the code** — walk through backend routes, frontend components, database schemas

## Running Locally

```bash
# Prerequisites: Docker, Anthropic API key
cp .env.example .env  # add your ANTHROPIC_API_KEY

# Start everything
docker compose -f docker-compose.dev.yml up --build

# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```
