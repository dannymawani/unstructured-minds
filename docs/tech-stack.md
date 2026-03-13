# Unstructured Minds - Tech Stack

## Overview

Unstructured Minds uses a modern, containerized web application stack that transforms natural language notes into structured, queryable data. The architecture prioritizes developer experience, performance, and maintainability.

### Core Philosophy

- **Web-first**: No Electron. Containerized web app for easy deployment.
- **Type-safe**: TypeScript frontend, Python type hints, Pydantic validation.
- **Real-time**: Server-sent events for streaming extraction progress.
- **Performant**: Vite for fast builds, DuckDB for columnar analytics, virtualized lists for large datasets.
- **Scalable**: FastAPI async support, DuckDB embedded OLAP efficiency.

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         User's Browser                            │
├──────────────────────────────────────────────────────────────────┤
│                         React 19 App                              │
│         (Milkdown Editor, Kanban, Charts, Settings)             │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP/WebSocket
                    ┌────────────▼────────────┐
                    │  Nginx (prod)           │
                    │  Vite Dev Server (dev)  │
                    └────────────┬────────────┘
                                 │ HTTP/SSE
┌────────────────────────────────▼─────────────────────────────────┐
│                        FastAPI Server                             │
│                    (Python 3.12+, async)                          │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ DuckDB       │  │ Anthropic    │  │ Filesystem           │   │
│  │ (Extracted   │  │ API Client   │  │ (Note storage)       │   │
│  │  Data)       │  │ (Claude)     │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Frontend

Frontend is a React 19 single-page application built with Vite, featuring a rich markdown editor (Milkdown), kanban task management, and data visualization.

### React 19

**Version**: 19 (latest)

**Why**: Latest major release includes concurrent features, automatic batching, and improved server component support. Provides the most modern React patterns and best performance characteristics.

**Usage**: Core UI framework for all interactive components. Concurrent rendering enables smooth user experience during heavy operations like bulk extraction.

### Milkdown 7

**Version**: 7

**Why**: ProseMirror-based WYSIWYG markdown editor. Provides a powerful editing experience with:
- Native markdown support (not a wrapper around other editors)
- Plugin ecosystem for custom commands
- Fine-grained control over rendering and serialization
- Extensible for skill buttons and custom marks

**Usage**: Primary text editor for daily notes. Replaces textarea with rich, real-time markdown preview. Integrates with React via controlled components pattern.

### Tailwind CSS 4

**Version**: 4 (with Vite plugin)

**Why**: Utility-first CSS framework integrated as Vite plugin for:
- Zero runtime overhead (compiled to static CSS)
- Consistent design system via CSS variables
- Dark mode support via class strategy
- Rapid prototyping with atomic utilities

**Connection**: Works with Vite plugin for on-demand CSS generation. CSS variables defined in project match brand guidelines (teal, dark, amber, etc.).

### Vite 7

**Version**: 7

**Why**: Modern build tool that replaces webpack/Create React App:
- Instant HMR (Hot Module Replacement) for development
- ES modules-native for faster dev server startup
- Optimized production builds with code splitting
- TypeScript support without compilation step

**Connection**: Powers local dev server on `localhost:5173`. In production, assets are pre-built and served by Nginx.

### React Router 7

**Version**: 7

**Why**: Client-side routing without page refreshes:
- URL-based navigation for browser back/forward support
- Layout nesting matches component hierarchy
- Loader patterns for data fetching before route transition
- Seamless integration with React 19

**Usage**: Navigation between Daily Notes, Data Queries, Goals, Kanban, and Settings. Each route maps to a top-level view.

### dnd-kit

**Library**: dnd-kit (drag-and-drop toolkit)

**Why**: Lightweight, accessible drag-and-drop for kanban boards:
- Zero dependencies
- Keyboard support for accessibility
- Modular (only import sensors/strategies needed)
- Works seamlessly with React hooks

**Usage**: Kanban task reordering, task status changes via drag.

### Lucide React

**Library**: Icon library

**Why**: Simple, consistent icon set as React components:
- Tree-shaking friendly (only imported icons are bundled)
- Customizable via props (size, color, stroke-width)
- Matches brand aesthetic

**Usage**: UI icons throughout app (check, X, menu, chevron, etc.).

### @tanstack/react-virtual

**Library**: React Virtual from TanStack

**Why**: Virtualization library for rendering large lists efficiently:
- Only visible items are rendered to DOM
- Smooth scrolling even with thousands of items
- Works with dynamic heights

**Usage**: Historical note list, exercise log tables, large query results.

### Vitest

**Framework**: Unit testing (Vitest)

**Why**: Modern test runner built on Vite:
- Uses same Vite config (no duplicate build setup)
- Fast execution via esbuild
- Compatible with Jest test syntax
- Native ESM and TypeScript support

**Usage**: Component tests, utility function tests. Run via `npm test`.

---

## Backend

Backend is a Python FastAPI application that handles data extraction, storage, and querying. It acts as the bridge between the React frontend and the data layer.

### Python >=3.12

**Version**: 3.12+ (feature branch minimum)

**Why**: Modern Python features:
- Type hints are now standard (improves code clarity)
- PEP 701 syntax for f-strings
- Better performance optimizations in interpreter
- Long-term support (LTS) for production stability

**Usage**: All backend code. Type hints on all function signatures (enforced via mypy/pyright).

### FastAPI

**Framework**: FastAPI (async web framework)

**Why**: Modern async-first framework:
- Automatic OpenAPI/Swagger documentation
- Built-in request/response validation via Pydantic
- Async support for I/O-bound operations (API calls, database)
- Dependency injection for cleaner code

**Connection**: Routes map to React endpoints. Uses SSE-Starlette for streaming extraction progress.

### DuckDB

**Database**: DuckDB 1.4 (embedded columnar OLAP)

**Why**: Embedded analytical database:
- No separate server process (embedded in FastAPI app)
- Columnar storage for aggregation queries (fast analytics)
- SQL interface for complex queries via natural language
- OLAP optimized (good for analytics, less so for OLTP)
- Compact file format (single `.duckdb` file)

**Connection**: FastAPI connects to DuckDB file at `data/unstructured.duckdb`. All extracted data (exercises, meals, sleep, etc.) stored in normalized tables.

**Data Schema Example**:
```sql
CREATE TABLE exercises (
    date TEXT,
    exercise_name TEXT,
    sets INTEGER,
    reps INTEGER,
    weight_kg FLOAT,
    duration_minutes FLOAT
);

CREATE TABLE meals (
    date TEXT,
    meal_type TEXT,
    description TEXT,
    calories INTEGER
);
```

### Anthropic SDK

**Library**: `anthropic` Python package

**Why**: Official SDK for Claude API:
- Type-safe client for all Claude models
- Streaming support for long responses
- Vision capabilities for image extraction (future)
- Handles authentication and rate limits

**Models Used**:
- **Claude Haiku 4.5**: Fast data extraction (exercises, meals, etc.)
- **Claude Sonnet 4.5**: Natural language queries over data (slower but smarter)

**Connection**: Extraction routes send note markdown to Claude. Query routes send natural language questions + DuckDB schema to Claude for SQL generation.

### Pydantic v2

**Library**: Pydantic v2 (data validation)

**Why**: Modern data validation and serialization:
- Type hints define schemas (no separate validation rules)
- Automatic conversion (string to int, etc.)
- JSON schema generation for OpenAPI docs
- Field validation with custom rules

**Usage**: All request bodies and response models validated via Pydantic. Example:

```python
class ExerciseLog(BaseModel):
    date: str  # YYYY-MM-DD
    exercise_name: str
    sets: int
    reps: int
    weight_kg: float | None = None
    duration_minutes: float | None = None
```

### structlog

**Library**: structlog (structured logging)

**Why**: Structured logging for observability:
- JSON output for log aggregation (ECS format)
- Context propagation (trace IDs, user IDs)
- Less verbose than print/logging

**Usage**: API logs, extraction logs, error tracking. Output to stdout for Docker container logs.

### slowapi

**Library**: slowapi (rate limiting)

**Why**: Rate limiting middleware for FastAPI:
- Per-endpoint rate limits
- Prevents abuse of Claude API
- Graceful 429 responses

**Usage**: Applied to extraction and query endpoints. Limits to 100 requests/minute per IP.

### SSE-Starlette

**Library**: SSE-Starlette (Server-Sent Events)

**Why**: Server-sent events for real-time progress updates:
- Streaming extraction progress (e.g., "Processing meals...", "Processing exercises...")
- Browser keeps connection open, server pushes updates
- No polling overhead

**Connection**: Bulk extraction endpoint returns `text/event-stream` response. Frontend listens via `EventSource` API.

---

## Infrastructure

Infrastructure spans development, testing, and production environments.

### Docker Compose

**Version**: Compose file format v3+

**Why**: Multi-container orchestration:
- Defines services (frontend, backend)
- Isolates dependencies (Python venv, Node modules)
- Development and production parity
- Easy local development setup

**Configs**:
- `docker-compose.dev.yml`: Hot-reload for development
  - Frontend: Vite dev server on port 5173
  - Backend: FastAPI with `--reload` flag on port 8000
  - Volumes: Live code reload
- `docker-compose.yml`: Production build
  - Frontend: Pre-built React SPA
  - Backend: Gunicorn/Uvicorn
  - Nginx: Reverse proxy and static file serving

**Usage**:
```bash
# Development
docker compose -f docker-compose.dev.yml up -d

# Production
docker compose up -d
```

### Nginx

**Role**: Production reverse proxy

**Why**: High-performance reverse proxy:
- Serves static frontend assets (React bundle, CSS, JS)
- Proxies API requests to FastAPI backend
- Gzip compression for assets
- SSL/TLS termination (in production)

**Configuration**:
```nginx
location / {
  # React SPA
  root /usr/share/nginx/html;
  try_files $uri /index.html;
}

location /api {
  # FastAPI backend
  proxy_pass http://backend:8000;
  proxy_set_header X-Forwarded-For $remote_addr;
}
```

**Not Used in Dev**: Dev uses Vite dev server for hot reload + direct FastAPI access.

---

## Testing

Testing spans both frontend and backend with appropriate frameworks.

### Vitest (Frontend)

**Framework**: Vitest

**Why**:
- Uses Vite config (no duplicate setup)
- Fast test execution
- Jest-compatible syntax

**Run**: `cd frontend && npm test`

**Coverage**: Component tests, utility tests, integration tests for core flows.

### Pytest (Backend)

**Framework**: Pytest

**Why**: Industry-standard Python testing:
- Fixtures for reusable test setup
- Parameterization for data-driven tests
- Plugin ecosystem (pytest-asyncio for async)

**Run**: `cd backend && pytest`

**Coverage**:
- Unit tests for extraction logic
- Integration tests for API endpoints
- Fixture-based DuckDB setup (in-memory test database)

**Async Support**: Uses `pytest-asyncio` for testing async endpoints.

---

## Development Dependencies

### Frontend

- **TypeScript**: Type checking
- **ESLint**: Code linting
- **Prettier**: Code formatting
- **ts-node**: TypeScript execution for scripts

### Backend

- **mypy**: Static type checking
- **black**: Code formatting
- **ruff**: Linting and import sorting
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

---

## Environment Variables

### Frontend (.env)

```bash
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_NAME=Unstructured Minds
```

### Backend (.env)

```bash
ANTHROPIC_API_KEY=sk-...
DATABASE_PATH=./data/unstructured.duckdb
LOG_LEVEL=INFO
RATE_LIMIT=100/minute
```

---

## Deployment Architecture

### Local Development

```
Browser (localhost:5173)
    ↓ (Vite dev server, auto-reload)
React App + Vite HMR
    ↓ (fetch to localhost:8000)
FastAPI (--reload)
    ↓
DuckDB file + Claude API
```

### Docker Compose Development

```
Browser (localhost:5173)
    ↓
docker service: frontend (Vite)
    ↓
docker service: backend (FastAPI --reload)
    ↓
Shared volume: data/
```

### Production (Docker Compose + Nginx)

```
Browser (example.com)
    ↓
Nginx container (port 80/443)
    ├─ Static files (React build)
    └─ /api proxy
        ↓
FastAPI container (gunicorn + uvicorn)
    ↓
DuckDB file + Claude API
```

---

## Performance Characteristics

| Component | Bottleneck | Mitigation |
|-----------|-----------|-----------|
| Frontend rendering | Large lists (1000+ items) | React Virtual virtualization |
| DuckDB queries | Complex aggregations | Column-oriented storage, indexing |
| Claude extraction | API latency (20-30s) | SSE streaming progress, batching |
| Asset delivery | Large JS bundle | Code splitting, tree-shaking |
| Network | JSON serialization | Compression via Nginx gzip |

---

## Version Pinning Strategy

- **Frontend**: `package-lock.json` pins exact versions
- **Backend**: `requirements.txt` pins major.minor versions (allows patch updates)
- **Python**: Minimum 3.12, no upper limit (modern LTS versions supported)

---

## Security Considerations

1. **API Key Management**: Anthropic API key in `.env.local` (never committed)
2. **Rate Limiting**: slowapi prevents Claude API abuse
3. **CORS**: FastAPI configured for development (no CORS in dev, restricted in prod)
4. **Input Validation**: Pydantic validates all incoming requests
5. **SQL Injection Prevention**: ORM patterns via Pydantic + SQL parameterization

---

## Future Tech Decisions

- **Vision Models**: Anthropic SDK supports image extraction (future for receipt photos, workout screenshots)
- **Caching**: Redis if needed for rate limit counters or session state
- **Observability**: Prometheus metrics export via FastAPI middleware
- **Alternative Databases**: Migration to PostgreSQL if multi-user support needed (DuckDB is single-file)

---

## Reference Documentation

- **Vite**: https://vitejs.dev/
- **React**: https://react.dev/
- **Milkdown**: https://milkdown.dev/
- **FastAPI**: https://fastapi.tiangolo.com/
- **DuckDB**: https://duckdb.org/
- **Tailwind CSS**: https://tailwindcss.com/
- **Docker Compose**: https://docs.docker.com/compose/
- **Pydantic**: https://docs.pydantic.dev/

