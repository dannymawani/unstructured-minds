# Development Guide

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker (optional, for containerized setup)

## Quick Setup

### With Docker (recommended)

```bash
cp .env.example .env
make dev
```

Frontend at http://localhost:5173, backend at http://localhost:8000.

### Without Docker

**Backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python3 -m uvicorn src.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Demo Mode

Seed the app with sample data to see it in action:

```bash
cd backend
python3 -m src.seed.demo_notes --vault-path ../vault --days 14
python3 -m src.seed.demo_data --data-path ../data --days 14
```

This creates 14 days of daily notes and structured data (exercises, meals, metrics).

## Running Tests

```bash
make test              # All tests
make test-backend      # Backend (pytest)
make test-frontend     # Frontend (vitest)
make typecheck         # TypeScript checking
```

### Backend test auth bypass

Tests automatically bypass authentication via an autouse fixture in `conftest.py`. See `ai_docs/08-auth-and-security.md` for details.

## Code Style

**Backend:** Ruff for linting and formatting. 100 char line length.
```bash
cd backend
ruff check .
ruff format .
```

**Frontend:** TypeScript strict mode. ESLint for linting.
```bash
cd frontend
npm run typecheck
```

## Project Structure

```
unstructured-minds/
├── backend/
│   ├── src/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── db/           # DuckDB + Postgres managers
│   │   ├── llm/          # LLM client (LiteLLM, provider-agnostic)
│   │   ├── extraction/   # Data extraction pipeline
│   │   ├── middleware/    # Auth, rate limiting, logging
│   │   ├── storage/      # File storage (local + Postgres)
│   │   ├── seed/         # Demo data generators
│   │   ├── config.py     # Environment configuration
│   │   └── main.py       # App entry point
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom React hooks
│   │   └── App.tsx       # Root component
│   └── public/
├── vault/                # Markdown notes (gitignored)
├── data/                 # DuckDB database (gitignored)
├── docs/                 # Documentation
├── ai_docs/              # Deep technical docs
├── docker-compose.yml    # Production
├── docker-compose.dev.yml # Development overrides
├── Makefile              # Common commands
└── .env.example          # Environment template
```

## Environment Variables

See `.env.example` for the full list. Key ones:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | auto-detected | `anthropic`, `openai`, `ollama` |
| `LLM_API_KEY` | — | API key for your provider |
| `STORAGE_MODE` | `local` | `local` (DuckDB) or `postgres` |
| `AUTH_MODE` | `none` | `none`, `basic`, `clerk` |
| `DEBUG` | `false` | Enable debug logging + hot reload |

## Useful Make Targets

```bash
make help         # Show all targets
make up           # Start local mode
make up-postgres  # Start with Postgres
make dev          # Start dev mode (hot reload)
make test         # Run all tests
make clean        # Remove containers and volumes
```
