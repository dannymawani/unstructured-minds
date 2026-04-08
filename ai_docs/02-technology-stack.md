# Technology Stack

Every technology used in Unstructured Minds, its version, purpose, and how it connects to the system.

## Core Philosophy

- **Web-first**: Containerized web app, no Electron
- **Type-safe**: TypeScript frontend, Python type hints, Pydantic validation
- **Real-time**: SSE for streaming extraction progress
- **Performant**: Vite builds, DuckDB columnar analytics, virtualized lists

## Frontend

| Technology | Version | Purpose | Connection |
|-----------|---------|---------|------------|
| React | 19 | Core UI framework | All interactive components, concurrent rendering |
| Vite | 7 | Build tool + dev server | HMR in dev, optimized production builds, code splitting |
| TypeScript | 5.9 (strict) | Type checking | All frontend code, enforced via `vite-plugin-checker` |
| Tailwind CSS | 4 | Utility-first CSS | Via `@tailwindcss/vite` plugin, CSS variables for theming |
| Milkdown | 7 | WYSIWYG markdown editor | ProseMirror-based, plugins: commonmark, gfm, history, slash menu |
| React Router | 7 | Client-side routing | URL-based navigation: Editor, Dashboard, Kanban, Calendar |
| Clerk React | 5 | Auth UI | `<SignedIn>`/`<SignedOut>` gates, token sync |
| @dnd-kit | core 6, sortable 10 | Drag-and-drop | Kanban task reordering and status changes |
| @tanstack/react-virtual | 3 | List virtualization | File tree, exercise log tables, large query results |
| lucide-react | latest | Icons | Tree-shakable SVG icons, 16/20/24px sizes |
| class-variance-authority | latest | Component variants | Button component styling |
| Vitest | 4 | Testing | Jest-compatible, shares Vite config |
| @testing-library/react | 16 | Component testing | DOM testing utilities |

## Backend

| Technology | Version | Purpose | Connection |
|-----------|---------|---------|------------|
| Python | >=3.12 | Runtime | Type hints, f-string syntax, modern features |
| FastAPI | >=0.115 | Web framework | Async endpoints, auto OpenAPI docs, DI |
| Uvicorn | latest (standard) | ASGI server | Runs FastAPI, async I/O |
| LiteLLM | >=1.40 | LLM abstraction | Provider-agnostic AI (Anthropic, OpenAI, Ollama, etc.) |
| DuckDB | >=1.0 | Embedded analytics DB | Columnar OLAP, single file, in-memory analytics cache |
| Pydantic | >=2.0 | Data validation | Request/response models, settings |
| pydantic-settings | latest | Config management | Env vars → typed Settings object |
| psycopg | >=3.2 (binary) | Postgres driver | Cloud mode connection pool |
| psycopg-pool | latest | Connection pooling | Cloud mode DB pool (min 2, max 10) |
| PyJWT | >=2.9 (crypto) | JWT handling | Clerk token verification (RS256) |
| httpx | >=0.27 | HTTP client | JWKS fetching from Clerk |
| structlog | >=24.0 | Structured logging | JSON output, context propagation |
| slowapi | >=0.1.9 | Rate limiting | Per-endpoint limits, prevents API abuse |
| sse-starlette | >=2.0 | Server-sent events | Streaming extraction progress |
| aiofiles | >=24.0 | Async file I/O | Vault file operations |
| python-dotenv | latest | Env file loading | `.env` file support |
| python-multipart | latest | Form data | File upload support |

## Dev Dependencies

| Technology | Purpose |
|-----------|---------|
| pytest >=8.0, pytest-asyncio, pytest-cov | Backend testing |
| ruff >=0.5 | Python linting + formatting |
| mypy >=1.10 | Static type checking |
| jsdom 27 | Frontend test DOM environment |
| rollup-plugin-visualizer | Bundle analysis (`npm run analyze`) |

## Infrastructure

| Technology | Purpose | Details |
|-----------|---------|---------|
| Docker Compose | Container orchestration | backend + frontend services |
| Nginx (alpine) | Production reverse proxy | Static files, `/api/*` proxy, gzip, CSP headers |
| Postgres | Cloud database | Any Postgres provider (Neon, Supabase, self-hosted) |
| Clerk | Authentication | Optional JWT-based auth (one of three auth modes) |
| GitHub Actions | CI/CD | Landing page deployment |

## AI Models

Configurable via `LLM_PROVIDER`, `LLM_MODEL_FAST`, and `LLM_MODEL_SMART` env vars.

| Role | Default (Anthropic) | Used For |
|------|-------------------|----------|
| Fast model (`llm_model_fast`) | Claude Haiku 4.5 | Extraction, classification, queries |
| Smart model (`llm_model_smart`) | Claude Sonnet 4.5 | Note editing, skill execution |

## Performance Characteristics

| Component | Bottleneck | Mitigation |
|-----------|-----------|------------|
| Frontend rendering | Large lists (1000+ items) | React Virtual virtualization |
| DuckDB queries | Complex aggregations | Column-oriented storage, indexing |
| Claude extraction | API latency (20-30s) | SSE streaming progress, batching |
| Asset delivery | Large JS bundle | Code splitting (vendor-react, vendor-milkdown, vendor-icons) |
| Network | JSON serialization | Nginx gzip compression |
