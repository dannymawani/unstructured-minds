# 08 - Architecture Diagrams

## Technology Stack (Latest Versions - January 2026)

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| **Frontend** | React | 19.2.4 | Released Jan 26, 2026 |
| | TypeScript | 5.9.3 | (6.0 bridge coming, 7.0 in Go) |
| | TipTap | 3.15.3 | Markdown WYSIWYG editor |
| | Vite | 6.x | Build tool |
| | Tailwind CSS | 4.x | Styling |
| | Zustand | 5.x | State management |
| | Recharts | 2.x | Charts/dashboards |
| **Desktop** | Electron | 40.0.0 | Released Jan 13, 2026 (Chromium 144, Node 24) |
| **Backend** | Python | 3.14.2 | Released Dec 5, 2025 |
| | FastAPI | 0.115.x | Latest with Python 3.14 support |
| | DuckDB | 1.4.4 | Released Jan 26, 2026 (LTS) |
| | Anthropic SDK | 0.45.x | Claude API client |
| | Watchdog | 6.x | File system monitoring |

---

## System Architecture

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                           ELECTRON SHELL (v40.0.0)                            ┃
┃                         Chromium 144 + Node.js 24                             ┃
┃ ┌───────────────────────────────────────────────────────────────────────────┐ ┃
┃ │                         REACT FRONTEND (v19.2.4)                          │ ┃
┃ │                                                                           │ ┃
┃ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │ ┃
┃ │  │   SIDEBAR   │  │   EDITOR    │  │    CHAT     │  │   DASHBOARD     │  │ ┃
┃ │  │             │  │             │  │             │  │                 │  │ ┃
┃ │  │ • File Tree │  │  TipTap     │  │ • NL Input  │  │ • Weekly View   │  │ ┃
┃ │  │ • Search    │  │  v3.15.3    │  │ • /skills   │  │ • Metrics       │  │ ┃
┃ │  │ • Quick     │  │             │  │ • History   │  │ • Trends        │  │ ┃
┃ │  │   Actions   │  │  Markdown   │  │             │  │                 │  │ ┃
┃ │  │             │  │  WYSIWYG    │  │             │  │  Recharts       │  │ ┃
┃ │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │ ┃
┃ │                                                                           │ ┃
┃ │  ┌─────────────────────────────────────────────────────────────────────┐  │ ┃
┃ │  │                    COMMAND PALETTE (⌘K)                             │  │ ┃
┃ │  │    /daily  /wod  /foodlog  /query  Settings  Open File  ...        │  │ ┃
┃ │  └─────────────────────────────────────────────────────────────────────┘  │ ┃
┃ │                                                                           │ ┃
┃ │  ┌─────────────────────────┐    ┌─────────────────────────────────────┐  │ ┃
┃ │  │      Zustand Store      │    │         React Query Cache          │  │ ┃
┃ │  │  • Current file         │    │  • API responses                   │  │ ┃
┃ │  │  • Editor state         │    │  • Dashboard data                  │  │ ┃
┃ │  │  • UI preferences       │    │  • File contents                   │  │ ┃
┃ │  └─────────────────────────┘    └─────────────────────────────────────┘  │ ┃
┃ └───────────────────────────────────────────────────────────────────────────┘ ┃
┃                                      │                                        ┃
┃                                      │ IPC / HTTP (localhost:8765)            ┃
┃                                      ▼                                        ┃
┃ ┌───────────────────────────────────────────────────────────────────────────┐ ┃
┃ │                      PYTHON BACKEND (FastAPI)                             │ ┃
┃ │                         Python 3.14.2                                     │ ┃
┃ │                                                                           │ ┃
┃ │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ ┃
┃ │  │   CLAUDE     │  │    SKILL     │  │     DATA     │  │    FILE      │  │ ┃
┃ │  │   SERVICE    │  │    ENGINE    │  │   EXTRACTOR  │  │   WATCHER    │  │ ┃
┃ │  │              │  │              │  │              │  │              │  │ ┃
┃ │  │ • Extraction │  │ • /daily     │  │ • Parse MD   │  │ • watchdog   │  │ ┃
┃ │  │ • Text2SQL   │  │ • /wod       │  │ • Validate   │  │ • Debounce   │  │ ┃
┃ │  │ • Chat       │  │ • /foodlog   │  │ • Transform  │  │ • Events     │  │ ┃
┃ │  │              │  │ • Custom     │  │              │  │              │  │ ┃
┃ │  │ Anthropic    │  │              │  │              │  │              │  │ ┃
┃ │  │ SDK v0.45    │  │              │  │              │  │              │  │ ┃
┃ │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │ ┃
┃ │                           │                                               │ ┃
┃ │                           ▼                                               │ ┃
┃ │  ┌─────────────────────────────────────────────────────────────────────┐  │ ┃
┃ │  │                       DuckDB v1.4.4 (LTS)                           │  │ ┃
┃ │  │                                                                     │  │ ┃
┃ │  │   exercise_log │ daily_metrics │ food_log │ tasks │ activities    │  │ ┃
┃ │  │                                                                     │  │ ┃
┃ │  └─────────────────────────────────────────────────────────────────────┘  │ ┃
┃ └───────────────────────────────────────────────────────────────────────────┘ ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      │
                                      │ File System
                                      ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                              LOCAL FILE SYSTEM                                ┃
┃                                                                               ┃
┃   vault/                    .unstructured/           data/                   ┃
┃   ├── Daily-Notes/          ├── config.json          └── exports/            ┃
┃   │   └── 2026-01/          ├── cache/                   ├── exercise.csv   ┃
┃   │       └── *.md          └── app.duckdb               └── metrics.csv    ┃
┃   ├── Training/                                                              ┃
┃   └── Work/                                                                  ┃
┃                                                                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      │
                                      │ HTTPS
                                      ▼
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                              EXTERNAL SERVICES                                ┃
┃                                                                               ┃
┃   ┌─────────────────────────────────────────────────────────────────────┐    ┃
┃   │                     Claude API (Anthropic)                          │    ┃
┃   │                                                                     │    ┃
┃   │   claude-sonnet-4  ──────  Fast extraction, queries                │    ┃
┃   │   claude-opus-4    ──────  Complex skills, reasoning               │    ┃
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
│   TipTap editor loads the new note                                          │
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
│       {"exercise": "squat", "weight_kg": 100, "reps": 5, "set_number": 1}   │
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
│   - exercise_log (date, exercise, weight_kg, reps, set_number...)          │
│   - activities (date, type, duration_minutes...)                            │
│   Generate ONLY the SQL query."                                             │
│                                                                              │
│   User: "How many times did I squat over 100kg this month?"                 │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   Response:                                                                  │
│   SELECT COUNT(DISTINCT date) as days                                       │
│   FROM exercise_log                                                         │
│   WHERE exercise ILIKE '%squat%'                                            │
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

## Component Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ELECTRON MAIN PROCESS                              │
│                                                                              │
│   ┌───────────────┐         ┌───────────────┐         ┌───────────────┐    │
│   │  App Startup  │────────▶│ Start Python  │────────▶│  Open Window  │    │
│   │               │         │ FastAPI       │         │               │    │
│   └───────────────┘         └───────────────┘         └───────────────┘    │
│                                    │                                        │
│                                    │ spawn child process                    │
│                                    ▼                                        │
│                           ┌───────────────┐                                 │
│                           │ Python Server │                                 │
│                           │ localhost:8765│                                 │
│                           └───────────────┘                                 │
│                                    │                                        │
└────────────────────────────────────│────────────────────────────────────────┘
                                     │
                          ┌──────────┴──────────┐
                          │                     │
                          ▼                     ▼
            ┌──────────────────────┐  ┌──────────────────────┐
            │  RENDERER PROCESS    │  │  RENDERER PROCESS    │
            │  (Main Window)       │  │  (Settings Window)   │
            │                      │  │                      │
            │  React App           │  │  React App           │
            │  ├── Editor          │  │  └── Settings        │
            │  ├── Sidebar         │  │                      │
            │  ├── Chat            │  │                      │
            │  └── Dashboard       │  │                      │
            └──────────────────────┘  └──────────────────────┘
                          │
                          │ HTTP requests
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
            │                                               │
            └──────────────────────────────────────────────┘
```

---

## Package.json Dependencies (Frontend)

```json
{
  "name": "unstructured-minds",
  "version": "0.1.0",
  "main": "electron/main.js",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "electron:dev": "concurrently \"vite\" \"electron .\"",
    "electron:build": "vite build && electron-builder"
  },
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "@tiptap/react": "^3.15.3",
    "@tiptap/starter-kit": "^3.15.3",
    "@tiptap/extension-markdown": "^3.15.3",
    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.60.0",
    "recharts": "^2.15.0",
    "lucide-react": "^0.470.0",
    "tailwindcss": "^4.0.0",
    "clsx": "^2.1.0"
  },
  "devDependencies": {
    "typescript": "^5.9.3",
    "vite": "^6.0.0",
    "electron": "^40.0.0",
    "electron-builder": "^25.0.0",
    "@types/react": "^19.0.0",
    "concurrently": "^9.0.0"
  }
}
```

---

## Requirements.txt (Backend)

```
# Python 3.14.2
fastapi==0.115.6
uvicorn[standard]==0.34.0
anthropic==0.45.0
duckdb==1.4.4
watchdog==6.0.0
pydantic==2.12.0
python-dotenv==1.0.1
httpx==0.28.0
```

---

*Back to: [README.md](./README.md)*

## Sources

- [React Versions](https://react.dev/versions) - React 19.2.4
- [Electron Releases](https://www.electronjs.org/docs/latest/tutorial/electron-timelines) - Electron 40.0.0
- [TipTap GitHub](https://github.com/ueberdosis/tiptap) - TipTap 3.15.3
- [DuckDB Release Calendar](https://duckdb.org/release_calendar) - DuckDB 1.4.4
- [FastAPI PyPI](https://pypi.org/project/fastapi/) - FastAPI 0.115.x
- [Python Downloads](https://www.python.org/downloads/) - Python 3.14.2
- [TypeScript Releases](https://github.com/microsoft/typescript/releases) - TypeScript 5.9.3
