# 02 - System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Compose                              │
├─────────────────────────────────┬───────────────────────────────┤
│         Frontend Container      │      Backend Container        │
│         (nginx:alpine)          │      (python:3.14-slim)       │
│  ┌───────────────────────────┐  │  ┌─────────────────────────┐  │
│  │    React SPA (Milkdown)   │  │  │   FastAPI Application   │  │
│  │  ┌───────┐ ┌───────────┐  │  │  │  ┌──────┐ ┌──────────┐ │  │
│  │  │Editor │ │ Dashboard │  │  │  │  │Claude│ │ DuckDB   │ │  │
│  │  └───────┘ └───────────┘  │  │  │  │Client│ │ Manager  │ │  │
│  │  ┌───────┐ ┌───────────┐  │  │  │  └──────┘ └──────────┘ │  │
│  │  │ Chat  │ │File Tree  │  │  │  │  ┌──────────────────┐  │  │
│  │  └───────┘ └───────────┘  │  │  │  │ Data Extractor   │  │  │
│  └───────────────────────────┘  │  │  └──────────────────┘  │  │
│         Port 80                 │  │  └─────────────────────────┘│
│              │                  │          Port 8000             │
└──────────────┼──────────────────┴───────────────┬───────────────┘
               │         HTTP/REST                │
               └──────────────────────────────────┘
                              │
                       Volume Mounts
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   ./vault/      │  │   ./data/       │  │   ./config/     │
│   *.md files    │  │   *.csv         │  │   settings      │
│                 │  │   *.duckdb      │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Deployment Size Comparison

| Approach | Size | Startup |
|----------|------|---------|
| **Web App (Docker)** | ~50MB images | <5s |
| Electron | ~200MB | 3-5s |
| Tauri | ~30MB | <2s |

---

## Architecture Options

### Option A: Tauri + React

**Stack:**
- Frontend: React + TypeScript
- Backend: Rust (Tauri)
- Database: DuckDB (Rust bindings)
- Editor: Milkdown

```
┌─────────────────────────────────────┐
│           Tauri Window              │
│  ┌───────────────────────────────┐ │
│  │      React Application        │ │
│  │  (TypeScript, Milkdown)       │ │
│  └───────────────────────────────┘ │
│                 │ IPC              │
│  ┌───────────────────────────────┐ │
│  │        Rust Backend           │ │
│  │  ┌─────────┐ ┌─────────────┐ │ │
│  │  │ DuckDB  │ │ File System │ │ │
│  │  └─────────┘ └─────────────┘ │ │
│  │  ┌─────────────────────────┐ │ │
│  │  │   Claude API Client     │ │ │
│  │  └─────────────────────────┘ │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
        Bundle size: ~15-30 MB
```

**Pros:**
- Small bundle size (no Chromium bundled, uses native webview)
- Rust backend is fast and memory-efficient
- Good DuckDB support in Rust
- Strong security model
- Cross-platform (macOS, Windows, Linux)

**Cons:**
- Rust learning curve if not familiar
- Smaller ecosystem than Electron
- Some webview inconsistencies across platforms

**Best for:** Production-quality app with performance focus

---

### Option B: Electron + React + Python

**Stack:**
- Frontend: React + TypeScript
- Backend: Python (FastAPI as sidecar)
- Database: DuckDB (Python bindings)
- Editor: Milkdown

```
┌─────────────────────────────────────┐
│         Electron Window             │
│  ┌───────────────────────────────┐ │
│  │      React Application        │ │
│  │  (TypeScript, Milkdown)       │ │
│  └───────────────────────────────┘ │
│                 │ HTTP             │
│  ┌───────────────────────────────┐ │
│  │    Python Sidecar (FastAPI)   │ │
│  │  ┌─────────┐ ┌─────────────┐ │ │
│  │  │ DuckDB  │ │   Scripts   │ │ │
│  │  └─────────┘ └─────────────┘ │ │
│  │  ┌─────────────────────────┐ │ │
│  │  │   Claude API Client     │ │ │
│  │  └─────────────────────────┘ │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
        Bundle size: ~150-200 MB
```

**Pros:**
- Reuse existing Python scripts directly
- Mature ecosystem
- Easy to prototype
- Consistent rendering (bundled Chromium)
- Huge community and resources

**Cons:**
- Large bundle size
- Higher memory usage
- Need to manage Python sidecar process
- Security model less strict than Tauri

**Best for:** Fast development, reusing existing Python code

---

### Option C: Tauri + React + Python Sidecar

**Stack:**
- Frontend: React + TypeScript
- Backend: Rust (Tauri) for core, Python for AI/skills
- Database: DuckDB (accessible from both)
- Editor: Milkdown

```
┌─────────────────────────────────────┐
│           Tauri Window              │
│  ┌───────────────────────────────┐ │
│  │      React Application        │ │
│  └───────────────────────────────┘ │
│         │ IPC           │ HTTP     │
│  ┌──────┴──────┐ ┌──────┴───────┐ │
│  │    Rust     │ │    Python    │ │
│  │   (files,   │ │   (Claude,   │ │
│  │   DuckDB)   │ │   skills)    │ │
│  └─────────────┘ └──────────────┘ │
└─────────────────────────────────────┘
        Bundle size: ~50-80 MB
```

**Pros:**
- Best of both: Rust performance + Python flexibility
- Reuse existing Python scripts
- Smaller than pure Electron
- Can migrate Python to Rust over time

**Cons:**
- Two backend languages to maintain
- More complex build/packaging
- Need to manage Python process

**Best for:** Pragmatic balance - ship fast, optimize later

---

### Option D: Web App (Next.js) + Local Server

**Stack:**
- Frontend: Next.js (static export)
- Backend: Python (FastAPI)
- Database: DuckDB
- Runs in browser, connects to local server

```
┌─────────────────────────────────────┐
│         Any Browser                 │
│  ┌───────────────────────────────┐ │
│  │    Next.js Static App         │ │
│  │    (served from localhost)    │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
                 │ HTTP
┌─────────────────────────────────────┐
│    Python Server (FastAPI)          │
│  ┌─────────┐ ┌─────────────────┐   │
│  │ DuckDB  │ │   File System   │   │
│  └─────────┘ └─────────────────┘   │
└─────────────────────────────────────┘
```

**Pros:**
- Fastest to develop
- Easy to iterate on UI
- No app packaging needed
- Can later wrap with Tauri/Electron

**Cons:**
- Not a "real" app (runs in browser)
- User must start server manually (or use launcher)
- Less polished experience
- File system access via API only

**Best for:** Rapid prototyping, validating UI/UX

---

## Recommendation

### ✅ Selected: Option D (Web App + Docker)

**Why:**
1. **Simplest architecture** - No Electron/Tauri complexity
2. **Easy deployment** - Docker Compose, runs anywhere
3. **Lighter footprint** - ~5MB frontend vs ~200MB Electron
4. **Containerized** - Reproducible, cloud-ready
5. **Milkdown works perfectly** - No desktop wrapper needed
6. **Focus on features** - Not app packaging

### Rejected Alternatives

| Option | Why Rejected |
|--------|--------------|
| Electron | Overkill for web app, 150-200MB bundle, complex |
| Tauri | Adds complexity without benefit for web deployment |
| Desktop-first | User wants Docker/containerized deployment |

---

## Component Breakdown

### Frontend Components

| Component | Purpose | Library |
|-----------|---------|---------|
| Markdown Editor | Write/edit notes | Milkdown |
| File Browser | Navigate vault | Custom tree component |
| Chat Interface | Natural language input | Custom |
| Command Palette | Quick actions, /skills | Custom (like VS Code) |
| Dashboard Panels | Visualize data | Recharts or Observable Plot |
| Settings Panel | Configuration | Custom |

### Backend Services

| Service | Purpose | Notes |
|---------|---------|-------|
| File Watcher | Detect changes | watchdog (Python) or notify (Rust) |
| Data Extractor | Parse notes → structured | Claude API + custom parsers |
| Skill Engine | Execute /commands | Port from current .claude/skills/ |
| DuckDB Manager | Query structured data | duckdb Python/Rust bindings |
| Claude Client | API communication | anthropic SDK |

---

## Data Flow

### Writing a Note

```
User types in editor
        │
        ▼
    Save file to vault/
        │
        ▼
    File watcher detects change
        │
        ▼
    Data extractor analyzes content
        │
        ▼
    Claude API extracts structured data
        │
        ▼
    Insert into DuckDB
        │
        ▼
    Dashboard auto-refreshes
```

### Natural Language Query

```
User types "How many workouts this week?"
        │
        ▼
    Claude interprets intent
        │
        ▼
    Generates DuckDB SQL query
        │
        ▼
    Execute query
        │
        ▼
    Format and display result
```

### Skill Execution

```
User types "/daily"
        │
        ▼
    Skill engine finds skill definition
        │
        ▼
    Claude executes skill with context
        │
        ▼
    Skill creates/modifies files
        │
        ▼
    UI updates with result
```

---

## Storage Abstraction Layer

The architecture includes a pluggable storage backend to support multiple storage options:

```
┌─────────────────────────────────────────────────────────────────┐
│                    StorageBackend Interface                      │
│  read() | write() | delete() | list() | exists()                │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ LocalFilesystem │  │  AzureBlobStore │  │    S3Backend    │
│   ✅ v1.0       │  │   🔜 Future     │  │   🔜 Future     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Implementation Priority

| Backend | Priority | Status |
|---------|----------|--------|
| Local Filesystem | 1 | First implementation |
| Azure Blob Storage | 2 | Future |
| AWS S3 | 3 | Future |
| GCP Cloud Storage | 4 | Future |

### Design Principles

- **Local-first**: App works fully offline, cloud is optional
- **Markdown stays source of truth**: Storage layer doesn't change semantics
- **DuckDB local**: Query engine always local, can sync .duckdb file
- **Pluggable**: New backends via interface implementation

---

## Open Technical Questions

1. **DuckDB location:** Single file or per-table files?
2. **Claude context:** How much vault content to include in prompts?
3. **Offline mode:** Cache Claude responses? Use local model fallback?
4. ~~**Sync:** If multi-device, how? (CRDTs? Git? Cloud?)~~ → Resolved via Storage Backend
5. **Skill format:** Keep current .md format or define new spec?
6. **Storage backend selection:** UI for switching backends? Migration tools?

---

*Next: [03-FRONTEND.md](./03-FRONTEND.md)*
