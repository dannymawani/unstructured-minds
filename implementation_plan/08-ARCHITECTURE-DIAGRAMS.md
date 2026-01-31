# 08 - Architecture Diagrams

## Technology Stack (January 2026)

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| **Frontend** | React | 19 | Pure web app (no Electron) |
| | TypeScript | 5.x | |
| | Milkdown | - | Markdown WYSIWYG editor (MIT) |
| | Vite | 6.x | Build tool |
| | Tailwind CSS | 4.x | Styling |
| | Zustand | 5.x | State management |
| | Recharts | 2.x | Charts/dashboards |
| **Deployment** | Docker | - | nginx:alpine + python:3.14-slim |
| **Backend** | Python | 3.12 | |
| | FastAPI | 0.115.x | |
| | DuckDB | 1.4 | Embedded analytics |
| | Anthropic SDK | 0.45.x | Claude API client |
| | Watchdog | 6.x | File system monitoring |
| **AI** | Claude Haiku | claude-3-5-haiku | Extraction (fast, cheap) |
| | Claude Sonnet | claude-sonnet-4 | Complex queries |

---

## System Architecture (Docker Compose)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                           DOCKER COMPOSE                                      ┃
┃                                                                               ┃
┃ ┌───────────────────────────────────┐  ┌───────────────────────────────────┐ ┃
┃ │      FRONTEND CONTAINER           │  │      BACKEND CONTAINER            │ ┃
┃ │      (nginx:alpine)               │  │      (python:3.14-slim)           │ ┃
┃ │                                   │  │                                   │ ┃
┃ │  ┌─────────────────────────────┐  │  │  ┌─────────────────────────────┐  │ ┃
┃ │  │    REACT SPA (Milkdown)     │  │  │  │   FastAPI Application      │  │ ┃
┃ │  │                             │  │  │  │                             │  │ ┃
┃ │  │  ┌─────────┐ ┌───────────┐  │  │  │  │  ┌────────┐ ┌───────────┐  │  │ ┃
┃ │  │  │ Editor  │ │ Dashboard │  │  │  │  │  │ Claude │ │  DuckDB   │  │  │ ┃
┃ │  │  │Milkdown │ │ Recharts  │  │  │  │  │  │ Client │ │  Manager  │  │  │ ┃
┃ │  │  └─────────┘ └───────────┘  │  │  │  │  │ Haiku  │ └───────────┘  │  │ ┃
┃ │  │  ┌─────────┐ ┌───────────┐  │  │  │  │  └────────┘                │  │ ┃
┃ │  │  │  Chat   │ │ File Tree │  │  │  │  │  ┌────────────────────┐   │  │ ┃
┃ │  │  └─────────┘ └───────────┘  │  │  │  │  │  Data Extractor    │   │  │ ┃
┃ │  └─────────────────────────────┘  │  │  │  └────────────────────┘   │  │ ┃
┃ │                                   │  │  └─────────────────────────────┘  │ ┃
┃ │        Port 80 (nginx)            │  │        Port 8000 (uvicorn)        │ ┃
┃ └───────────────────────────────────┘  └───────────────────────────────────┘ ┃
┃                    │                              │                          ┃
┃                    └──────────── HTTP ───────────┘                          ┃
┃                                                                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      │
                               Volume Mounts
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  ./vault/       │         │  ./data/        │         │  ./config/      │
│  ├── Daily-Notes│         │  ├── app.duckdb │         │  └── settings   │
│  │   └── *.md   │         │  ├── exercise.csv│        │                 │
│  ├── Training/  │         │  ├── food.csv   │         │                 │
│  └── Work/      │         │  └── metrics.csv│         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                              EXTERNAL SERVICES                                ┃
┃                                                                               ┃
┃   ┌─────────────────────────────────────────────────────────────────────┐    ┃
┃   │                     Claude API (Anthropic)                          │    ┃
┃   │                                                                     │    ┃
┃   │   claude-3-5-haiku ──────  Extraction, SQL (fast & cheap)          │    ┃
┃   │   claude-sonnet-4  ──────  Complex skills, reasoning               │    ┃
┃   │                                                                     │    ┃
┃   └─────────────────────────────────────────────────────────────────────┘    ┃
┃                                                                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## Storage Backend Architecture

The storage layer is abstracted to support multiple backends. Local filesystem is the first implementation, with cloud storage options planned for future releases.

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                         STORAGE ABSTRACTION LAYER                             ┃
┃                                                                               ┃
┃   class StorageBackend(Protocol):                                            ┃
┃       async def read(path: str) -> bytes                                     ┃
┃       async def write(path: str, content: bytes) -> None                     ┃
┃       async def delete(path: str) -> None                                    ┃
┃       async def list(prefix: str) -> list[str]                               ┃
┃       async def exists(path: str) -> bool                                    ┃
┃                                                                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                     │
            ┌────────────────────────┼────────────────────────┐
            │                        │                        │
            ▼                        ▼                        ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  LocalFilesystem  │  │   AzureBlobStore  │  │     S3Backend     │
│                   │  │                   │  │                   │
│  ✅ First impl    │  │  🔜 Future        │  │  🔜 Future        │
│                   │  │                   │  │                   │
│  - Direct I/O     │  │  - azure-storage  │  │  - boto3          │
│  - watchdog       │  │  - blob SDK       │  │  - aioboto3       │
│  - Fast, simple   │  │  - Event Grid     │  │  - S3 events      │
└───────────────────┘  └───────────────────┘  └───────────────────┘
            │                        │                        │
            ▼                        ▼                        ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  ~/vault/         │  │  Azure Blob       │  │  S3 Bucket        │
│  ├── Daily-Notes/ │  │  Container        │  │  my-vault/        │
│  └── Training/    │  │                   │  │                   │
└───────────────────┘  └───────────────────┘  └───────────────────┘

                        ┌───────────────────┐
                        │   GCPCloudStore   │
                        │                   │
                        │  🔜 Future        │
                        │                   │
                        │  - google-cloud   │
                        │  - storage SDK    │
                        └───────────────────┘
                                 │
                                 ▼
                        ┌───────────────────┐
                        │  GCS Bucket       │
                        │  my-vault/        │
                        └───────────────────┘
```

### Storage Backend Selection

| Backend | Status | Use Case |
|---------|--------|----------|
| **Local Filesystem** | ✅ v1.0 | Default, fastest, offline |
| **Azure Blob Storage** | 🔜 Future | Enterprise, Azure ecosystem |
| **AWS S3** | 🔜 Future | AWS ecosystem, widely used |
| **GCP Cloud Storage** | 🔜 Future | GCP ecosystem |

### Key Design Principles

1. **Local-first** - Always works offline, cloud is optional sync
2. **Markdown source of truth** - Storage backend doesn't change data semantics
3. **DuckDB stays local** - Query engine runs locally, syncs .duckdb file
4. **Pluggable** - Add new backends without changing core code

---

## Daily Logging Flow

This flowchart shows what happens when a user creates a daily note and logs activities.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER CLICKS "DAILY NOTE" BUTTON                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SKILL ENGINE                                    │
│                                                                              │
│   1. Load /daily skill definition                                           │
│   2. Gather context:                                                        │
│      • Yesterday's note (for task rollover)                                 │
│      • Current date/time                                                    │
│      • Active injuries/constraints                                          │
│      • Calendar events (if integrated)                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLAUDE API CALL                                 │
│                                                                              │
│   System: "Create a daily note with task rollover, workout section..."      │
│   Context: Yesterday's incomplete tasks, today's date, injury status        │
│                                                                              │
│   ───────────────────────────────────────────────────────────────────────   │
│                                                                              │
│   Response: Complete markdown note with structure                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WRITE FILE TO VAULT                                  │
│                                                                              │
│   vault/Daily-Notes/2026-01/2026-01-31.md                                   │
│                                                                              │
│   # Daily Note - 2026-01-31                                                 │
│                                                                              │
│   ## Tasks                                                                   │
│   - [ ] Rolled over task from yesterday                                     │
│   - [ ] New task for today                                                  │
│                                                                              │
│   ## Workout                                                                 │
│   | Exercise | Weight | Reps | Sets |                                       │
│   |----------|--------|------|------|                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OPEN IN EDITOR                                     │
│                                                                              │
│   Milkdown editor loads the new note                                        │
│   User sees formatted markdown                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        │                                                           │
        ▼                                                           ▼
┌───────────────────────┐                               ┌───────────────────────┐
│   USER TYPES IN       │                               │   USER TYPES IN       │
│   WORKOUT TABLE       │                               │   CHAT: "/foodlog     │
│                       │                               │   breakfast: oatmeal  │
│   | squat | 100 | 5 | │                               │   with blueberries"   │
│                       │                               │                       │
└───────────────────────┘                               └───────────────────────┘
        │                                                           │
        ▼                                                           ▼
┌───────────────────────┐                               ┌───────────────────────┐
│   AUTO-SAVE           │                               │   SKILL ENGINE        │
│   (debounced 2s)      │                               │   executes /foodlog   │
│                       │                               │                       │
└───────────────────────┘                               └───────────────────────┘
        │                                                           │
        ▼                                                           ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          FILE WATCHER DETECTS CHANGE                          │
└───────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            DATA EXTRACTION                                    │
│                                                                               │
│   1. Hash file content                                                        │
│   2. Check extraction_log (skip if unchanged)                                │
│   3. Parse markdown structure                                                │
│   4. Send to Claude for extraction                                           │
│                                                                               │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                               │
│   Claude returns structured JSON:                                            │
│   {                                                                          │
│     "exercise_log": [                                                        │
│       {"exercise_name": "squat", "weight_kg": 100, "reps": 5, "set_number": 1}│
│     ],                                                                       │
│     "food_log": [                                                            │
│       {"meal_type": "breakfast", "description": "oatmeal with blueberries"} │
│     ],                                                                       │
│     "tasks": [                                                               │
│       {"description": "Rolled over task", "status": "pending"}              │
│     ]                                                                        │
│   }                                                                          │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            VALIDATE & UPSERT                                  │
│                                                                               │
│   1. Validate JSON against schema                                            │
│   2. Delete old records for this source_file                                 │
│   3. Insert new records into DuckDB                                          │
│   4. Update extraction_log with new hash                                     │
│                                                                               │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                               │
│   DuckDB Tables Updated:                                                     │
│   • exercise_log    (+1 row)                                                 │
│   • food_log        (+1 row)                                                 │
│   • tasks           (+2 rows)                                                │
│   • extraction_log  (hash updated)                                           │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          DASHBOARD AUTO-REFRESH                               │
│                                                                               │
│   React Query invalidates cache                                              │
│   Dashboard components re-fetch data                                         │
│   User sees updated charts                                                   │
│                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Weekly Activity                                                     │   │
│   │  ████  ██  ████  ░░  ░░  ░░  ░░                                    │   │
│   │  Mon  Tue  Wed  Thu  Fri  Sat  Sun                                  │   │
│   │                    ▲                                                 │   │
│   │                    │                                                 │   │
│   │              Today's workout added                                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Natural Language Query Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│   USER TYPES: "How many times did I squat over 100kg this month?"           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTENT DETECTION                                │
│                                                                              │
│   Is this a:                                                                │
│   ├── Data query?     → Generate SQL                                       │
│   ├── Skill request?  → Execute skill                                      │
│   ├── Knowledge ask?  → Search notes + respond                             │
│   └── Action?         → Perform action                                     │
│                                                                              │
│   Detected: DATA QUERY                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLAUDE TEXT-TO-SQL                                 │
│                                                                              │
│   System: "You are a SQL assistant for DuckDB. Tables available:            │
│   - exercise_log (date, exercise_name, weight_kg, reps, set_number...)     │
│   - activities (date, activity_type, duration_minutes...)                   │
│   Generate ONLY the SQL query."                                             │
│                                                                              │
│   User: "How many times did I squat over 100kg this month?"                 │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   Response:                                                                  │
│   SELECT COUNT(DISTINCT date) as days                                       │
│   FROM exercise_log                                                         │
│   WHERE exercise_name ILIKE '%squat%'                                            │
│     AND weight_kg > 100                                                     │
│     AND date >= DATE_TRUNC('month', CURRENT_DATE)                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            VALIDATE SQL                                      │
│                                                                              │
│   ✓ Starts with SELECT                                                      │
│   ✓ No INSERT/UPDATE/DELETE/DROP                                            │
│   ✓ EXPLAIN succeeds                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXECUTE ON DUCKDB                                   │
│                                                                              │
│   Result: [{"days": 6}]                                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FORMAT RESPONSE                                      │
│                                                                              │
│   "You squatted over 100kg on 6 different days this month."                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DISPLAY IN CHAT                                     │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  You: How many times did I squat over 100kg this month?             │   │
│   │                                                                      │   │
│   │  Assistant: You squatted over 100kg on 6 different days this       │   │
│   │  month.                                                              │   │
│   │                                                                      │   │
│   │  [Show SQL] [Add to dashboard]                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Communication (Docker)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           docker-compose up                                  │
│                                                                              │
│   ┌───────────────┐         ┌───────────────┐         ┌───────────────┐    │
│   │  Start nginx  │         │ Start uvicorn │         │  Mount        │    │
│   │  (frontend)   │         │ (backend)     │         │  Volumes      │    │
│   └───────────────┘         └───────────────┘         └───────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                        ┌────────────┴────────────┐
                        ▼                         ▼
          ┌──────────────────────┐    ┌──────────────────────┐
          │  BROWSER (any)       │    │  BACKEND CONTAINER    │
          │                      │    │                       │
          │  React SPA           │───▶│  FastAPI Server       │
          │  ├── Editor          │    │  localhost:8000       │
          │  ├── Sidebar         │    │                       │
          │  ├── Chat            │    │                       │
          │  └── Dashboard       │    │                       │
          │                      │    │                       │
          │  localhost:80        │    │                       │
          └──────────────────────┘    └──────────────────────┘
                        │
                        │ HTTP requests (fetch/axios)
                        ▼
          ┌──────────────────────────────────────────────┐
          │              FastAPI Server                   │
          │                                               │
          │  GET  /vault/files      → List files         │
          │  GET  /vault/file       → Read file          │
          │  POST /vault/file       → Write file         │
          │  POST /extract          → Extract data       │
          │  POST /query            → NL query           │
          │  POST /query/sql        → Direct SQL         │
          │  GET  /skills           → List skills        │
          │  POST /skills/{name}    → Execute skill      │
          │  GET  /dashboard/*      → Dashboard data     │
          │  GET  /health           → Health check       │
          │                                               │
          └──────────────────────────────────────────────┘
```

---

## Package.json Dependencies (Frontend)

```json
{
  "name": "unstructured-minds-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@milkdown/core": "^7.0.0",
    "@milkdown/react": "^7.0.0",
    "@milkdown/preset-commonmark": "^7.0.0",
    "@milkdown/theme-nord": "^7.0.0",
    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.0.0",
    "recharts": "^2.15.0",
    "lucide-react": "^0.470.0",
    "clsx": "^2.1.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "vite": "^6.0.0",
    "@types/react": "^19.0.0",
    "tailwindcss": "^4.0.0",
    "vitest": "^2.0.0"
  }
}
```

> **Note:** No Electron dependencies. This is a standard Vite + React web app.

---

## Requirements.txt (Backend)

```
# Python 3.14
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
anthropic>=0.40.0
duckdb>=1.0.0
watchdog>=4.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.27.0
```

---

## docker-compose.yml

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ${VAULT_PATH:-./vault}:/app/vault
      - ${DATA_PATH:-./data}:/app/data
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

*Back to: [README.md](./README.md)*
