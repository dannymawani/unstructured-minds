# 06 - Implementation Roadmap

## Phased Approach

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Phase 0       │  Phase 1       │  Phase 2       │  Phase 3             │
│  Foundation    │  Core MVP      │  Polish        │  Deployment          │
├──────────────────────────────────────────────────────────────────────────┤
│  • Project     │  • Editor      │  • Dashboard   │  • Docker config     │
│    setup       │  • Chat        │    views       │  • Documentation     │
│  • FastAPI     │  • Skills      │  • Settings    │  • Production        │
│    server      │  • Auto-log    │  • Themes      │    readiness         │
│  • DuckDB      │  • Daily note  │  • Polish UX   │                      │
│    schema      │    button      │                │                      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
unstructured-minds/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── claude/              # LLM integration
│   │   ├── db/                  # DuckDB
│   │   ├── storage/             # Storage abstraction
│   │   ├── api/                 # API routes
│   │   └── watcher/             # File watcher
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom hooks
│   │   ├── stores/              # Zustand stores
│   │   └── App.tsx
│   ├── Dockerfile
│   └── package.json
├── skills/                       # Skill definitions
├── docker-compose.yml
└── .env.example
```

---

## Phase 0: Foundation

**Goal:** Working backend with core APIs

| Deliverable | Description |
|-------------|-------------|
| Project structure | Directories, config files |
| FastAPI server | Running on localhost:8000 |
| DuckDB schema | Tables initialized |
| Storage layer | LocalFilesystem backend |
| Claude client | Anthropic SDK wrapper |
| Docker setup | docker-compose.yml working |

---

## Phase 1: Core MVP

**Goal:** Usable app with core features

| Deliverable | Description |
|-------------|-------------|
| Milkdown editor | WYSIWYG markdown editing |
| File browser | Vault navigation sidebar |
| Chat interface | Natural language input |
| Daily note button | One-click creation |
| Auto-extraction | On file save |
| Basic skills | /daily, /wod |

---

## Phase 2: Polish

**Goal:** Refined UX, dashboards, settings

| Deliverable | Description |
|-------------|-------------|
| Dashboard views | Weekly activity, metrics trends |
| Settings panel | Vault path, API key, theme |
| Dark mode | Theme toggle |
| Keyboard shortcuts | Cmd+K, Cmd+S, etc. |
| Error handling | Notifications, loading states |

---

## Phase 3: Deployment

**Goal:** Containerized web app ready for deployment

| Deliverable | Description |
|-------------|-------------|
| Production Dockerfiles | Multi-stage builds |
| docker-compose.prod.yml | Production configuration |
| Health checks | Container monitoring |
| Documentation | Deployment guide |

---

## API Endpoints

```
# Health
GET  /health

# Vault
GET  /vault/files
GET  /vault/file?path=...
POST /vault/file

# Extraction
POST /extract
POST /extract/batch

# Query
POST /query
POST /query/sql

# Skills
GET  /skills
POST /skills/{name}

# Dashboard
GET  /dashboard/weekly-activity
GET  /dashboard/metrics
```

---

## Testing Strategy

| Layer | Tool | Focus |
|-------|------|-------|
| Backend | pytest | API endpoints, extraction, DuckDB |
| Frontend | Vitest | Components, hooks, stores |
| E2E | Playwright | Full user flows |

---

See [09-IMPLEMENTATION-PLAN-AND-STEPS.md](./09-IMPLEMENTATION-PLAN-AND-STEPS.md) for detailed step-by-step tasks with tests.

---

*Next: [07-DECISIONS.md](./07-DECISIONS.md)*
