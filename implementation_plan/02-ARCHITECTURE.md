# 02 - System Architecture

## Selected Architecture: Docker Web App

Based on DECISION-015, we chose a containerized web application over desktop wrappers (Electron/Tauri).

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

### Why Docker Web App?

| Benefit | Description |
|---------|-------------|
| **Simple** | No Electron/Tauri complexity, IPC, or desktop packaging |
| **Portable** | Docker Compose runs anywhere - local, cloud, CI |
| **Light** | ~50MB images vs ~200MB Electron |
| **Containerized** | Reproducible builds, easy deployment |
| **Focus** | Build features, not app packaging |

### Rejected Alternatives

| Option | Why Rejected |
|--------|--------------|
| Electron | 150-200MB bundle, overkill for web app, complex packaging |
| Tauri | Adds complexity without benefit for Docker deployment |
| Tauri + Python sidecar | Two backend languages, complex build process |
| Desktop-first | User wants containerized deployment, not installers |

---

## Component Breakdown

### Frontend Components

| Component | Purpose | Library |
|-----------|---------|---------|
| Markdown Editor | Write/edit notes | Milkdown |
| File Browser | Navigate vault | Custom tree component |
| Chat Interface | Natural language input | Custom |
| Command Palette | Quick actions, /skills | Custom (like VS Code) |
| Dashboard Panels | Visualize data | Recharts |
| Settings Panel | Configuration | Custom |

### Backend Services

| Service | Purpose | Notes |
|---------|---------|-------|
| File Watcher | Detect changes | watchdog (Python) |
| Data Extractor | Parse notes → structured | Claude API + custom parsers |
| Skill Engine | Execute /commands | Port from current .claude/skills/ |
| DuckDB Manager | Query structured data | duckdb Python bindings |
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

1. **DuckDB location:** Single file or per-table files? --> single file if that is the easiest
2. **Claude context:** How much vault content to include in prompts? --> make it flexible and context based
3. **Offline mode:** Cache Claude responses? Use local model fallback? --> yes
4. ~~**Sync:** If multi-device, how? (CRDTs? Git? Cloud?)~~ → Resolved via Storage Backend
5. **Skill format:** Keep current .md format or define new spec? --> new spec but stil .md
6. **Storage backend selection:** UI for switching backends? Migration tools? --> not sure

---

*Next: [03-FRONTEND.md](./03-FRONTEND.md)*
