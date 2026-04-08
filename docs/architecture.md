# Architecture Overview

## System Design

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                             │
│         React 19 + Milkdown Editor + Tailwind            │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
              ┌──────────▼──────────┐
              │    FastAPI Backend   │
              │   (Python 3.12+)    │
              └──┬───────┬───────┬──┘
                 │       │       │
         ┌───────▼─┐ ┌───▼───┐ ┌─▼────────┐
         │ LiteLLM │ │DuckDB │ │ Postgres  │
         │ (any AI)│ │(local)│ │ (cloud)   │
         └─────────┘ └───────┘ └──────────┘
```

## Two Storage Modes

### Local Mode (default)

- **DuckDB** handles everything: storage + analytics
- Notes stored on the filesystem at `VAULT_PATH`
- Single file database at `DATA_PATH/unstructured.duckdb`
- Zero external dependencies

### Postgres Mode

- **Postgres** is the source of truth for all data
- **DuckDB** runs in-memory as an analytics cache
- Notes stored in Postgres (supports multi-user)
- Enable with `STORAGE_MODE=postgres` + `DATABASE_URL`

## Why Two Database Engines?

**DuckDB** is a column-oriented analytical database. It excels at aggregations, time-series queries, and "what did I eat last week?" type questions. It runs embedded — no server, just a file.

**Postgres** is a row-oriented relational database. It excels at transactional writes, concurrent access, and durability. It's what you need for production multi-user deployments.

In Postgres mode, the app loads data from Postgres into an in-memory DuckDB instance for fast analytical queries. This gives you the best of both worlds: Postgres durability with DuckDB query speed.

## AI Integration

The LLM layer is provider-agnostic via LiteLLM:

```
User writes note
    │
    ▼
Extraction API ──► LLMClient.extract() ──► Structured data ──► Database
    │
    ▼
Query API ──► LLMClient.complete() ──► SQL generation ──► DuckDB ──► Answer
```

**AI is optional.** The app works as a full notes + task management app without any API key. AI features (extraction, queries, chat, insights) require a configured provider.

### Supported providers

Any LiteLLM-compatible provider works. Tested with:
- **Anthropic** (Claude) — default, best results
- **OpenAI** (GPT-4o) — full feature support
- **Ollama** (local models) — free, no API key needed

## Authentication

Three modes, configured via `AUTH_MODE`:

| Mode | How it works |
|------|-------------|
| `none` | No auth. Single implicit user. Default for local/self-hosted. |
| `basic` | HTTP Basic Auth. Username/password from env vars. |
| `clerk` | Clerk JWT verification. Multi-user with per-user data isolation. |

## Key Directories

| Path | Purpose |
|------|---------|
| `backend/src/api/` | FastAPI route handlers |
| `backend/src/llm/` | Provider-agnostic LLM client |
| `backend/src/db/` | DuckDB + Postgres database managers |
| `backend/src/extraction/` | Data extraction pipeline |
| `backend/src/middleware/` | Auth, rate limiting, logging |
| `backend/src/storage/` | File storage abstraction (local + Postgres) |
| `frontend/src/components/` | React components |
| `ai_docs/` | Deep technical documentation |
