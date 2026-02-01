# 07 - Decision Log

This document tracks key architectural and technical decisions. Use this to understand **why** certain choices were made.

---

## Decision Template

```
## [DECISION-XXX] Title

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deprecated | Superseded by DECISION-XXX
**Deciders:** Who made this decision

### Context
What is the issue we're trying to solve?

### Options Considered
1. Option A - description
2. Option B - description

### Decision
What was decided and why.

### Consequences
What are the results of this decision?
```

---

## Decisions

---

## [DECISION-001] No Obsidian Plugin

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
The initial proposal considered building an Obsidian plugin as the fastest path to POC. However, this creates a dependency on Obsidian and limits customization.

### Options Considered
1. **Obsidian Plugin** - Build within Obsidian ecosystem
2. **Standalone App** - Build custom application

### Decision
Build a **standalone application** that:
- Reads/writes the same markdown file structure
- Works independently of Obsidian
- Can still be used alongside Obsidian if desired

### Consequences
- More development effort upfront
- Full control over UX
- Can evolve independently
- Users don't need Obsidian license
- Need to build or integrate markdown editor

---

## [DECISION-002] Markdown Files as Source of Truth

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Data can live in markdown (human-readable), DuckDB (queryable), or both. Need to establish which is authoritative.

### Options Considered
1. **Markdown primary** - DuckDB is derived/cached view
2. **DuckDB primary** - Markdown is generated output
3. **Dual primary** - Both are authoritative (sync required)

### Decision
**Markdown is the source of truth.** DuckDB is a derived view that can be fully regenerated from markdown files.

### Consequences
- Users can edit files with any editor
- DuckDB can be deleted and rebuilt anytime
- Extraction must be idempotent
- Some data (aggregations, computed fields) only lives in DuckDB
- Git version control works naturally

---

## [DECISION-003] Claude as Optional Intelligence Layer

**Date:** 2026-01-31
**Status:** Accepted (Updated)
**Deciders:** Danny

### Context
Need an LLM for data extraction, query understanding, and skill execution. Options include Claude API, OpenAI, local models. Also need to decide if Claude is required or optional.

### Options Considered
1. **Claude API required** - App needs Claude to function
2. **Claude API optional** - Core app works without it, Claude adds enhanced features
3. **Local LLM only** - Ollama, llama.cpp
4. **Hybrid** - Claude primary, local fallback

### Decision
**Claude API is optional** - core app works fully without it. Claude adds enhanced features when API key is provided.

**Core app (no Claude required):**
- View/edit markdown notes
- Browse file tree
- Manual data entry via forms
- Query existing DuckDB data with SQL
- Dashboard visualizations
- CSV export/import

**With Claude (enhanced features):**
- Automatic extraction from unstructured text
- Natural language queries
- Smart suggestions and insights
- Skill execution with AI reasoning
- Schema inference from examples

**CLI-first testing:**
- Extraction scripts runnable from command line
- Testable via Claude Code or terminal
- No web UI required for development/testing

### Consequences
- Zero barrier to start using the app
- No API costs until user wants AI features
- Core app is fully testable offline
- Claude is an "upgrade," not a requirement
- API key entered in settings when ready
- CLI scripts enable rapid iteration during development

---

## [DECISION-004] DuckDB for Analytics

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Need a query engine for structured data. Options include SQLite, DuckDB, PostgreSQL, or no SQL (just process CSVs).

### Options Considered
1. **DuckDB** - Embedded analytical database
2. **SQLite** - Traditional embedded database
3. **PostgreSQL** - Full database server
4. **Raw CSVs** - Query with pandas/polars

### Decision
**DuckDB** for its analytical capabilities, embedded nature, and excellent CSV support.

### Consequences
- Single file database, easy to manage
- Excellent for aggregations and time-series
- Can query CSV files directly without import
- 20MB added to bundle size
- Modern SQL features (window functions, CTEs)

---

## [DECISION-005] React + Milkdown for Frontend

**Date:** 2026-01-31
**Status:** Accepted (Updated)
**Deciders:** Danny

### Context
Need to choose frontend framework and markdown editor. Must be fully open source with no paid tiers.

### Options Considered
1. **React + TipTap** - Popular, but Pro features are paid
2. **React + Milkdown** - Fully MIT licensed, built on ProseMirror
3. **React + Lexical** - Meta's editor, MIT licensed
4. **Svelte + Milkdown** - Smaller bundle
5. **Flutter** - Cross-platform with Dart

### Decision
**React 19 + Milkdown** for fully open source stack with no paid tier concerns.

**Why Milkdown over TipTap:**
- 100% MIT licensed - no paid features to worry about
- Built on ProseMirror (same foundation as TipTap)
- Plugin-based architecture
- Good markdown support
- Active development

### Consequences
- Large React ecosystem of components
- Fully open source, no licensing concerns
- Plugin system for extensibility
- May have smaller community than TipTap
- Good documentation available

---

## [DECISION-006] Electron for Desktop

**Date:** 2026-01-31
**Status:** ~~Accepted~~ **Superseded by DECISION-015**
**Deciders:** Danny

### Context
Need to decide on application packaging strategy for desktop distribution.

### Options Considered
1. **Tauri** - Rust backend, native webview, small bundle (15-30MB)
2. **Electron** - Node backend, bundled Chromium, large bundle (150-200MB)
3. **Flutter** - Dart, custom rendering engine
4. **Web app only** - No packaging, browser-based

### Decision
~~**Electron 40.0.0** for desktop packaging.~~

**SUPERSEDED:** See DECISION-015 - Web App with Docker.

---

## [DECISION-015] Web App with Docker (No Electron)

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny
**Supersedes:** DECISION-006

### Context
Re-evaluating the need for Electron. Primary deployment goal is a containerized web app that can be pushed with Docker, not a desktop installer.

### Options Considered
1. **Electron** - Desktop app, large bundle, complex packaging
2. **Tauri** - Lighter desktop app, still desktop-focused
3. **Web App + Docker** - Pure web, containerized, simple deployment

### Decision
**Web App with Docker Compose** - no Electron.

Reasons:
- **User's primary goal is Docker deployment** - Electron is overkill
- **50x smaller** - ~5MB frontend vs ~200MB Electron
- **Simpler architecture** - No desktop wrapper, IPC, or packaging
- **Milkdown works in browser** - No desktop wrapper needed
- **Cloud-ready** - Easy to deploy to any platform
- **Faster development** - Focus on features, not app packaging

### Consequences
- Runs in browser, not as native app
- No offline-first (can add PWA/service workers later if needed)
- File access via API upload instead of native filesystem
- Significantly simpler CI/CD
- Can wrap with Tauri/Electron later if desktop distribution needed

---

## [DECISION-007] Keep Existing Python Scripts

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Existing Python scripts handle extraction, skills, and data processing. Should we rewrite in Rust/TypeScript or wrap existing code?

### Options Considered
1. **Wrap in FastAPI** - Expose existing scripts via API
2. **Rewrite in Rust** - Performance, single binary, tiny Docker image
3. **Rewrite in TypeScript** - Same language as frontend
4. **Hybrid** - Critical paths in Rust, logic in Python

### Decision
**Wrap existing Python scripts** in FastAPI to ship fast.

### Future Consideration: Rust Rewrite
Revisit Rust rewrite once app is stable, if:
- Performance bottlenecks are identified
- Docker image size becomes a concern (~150MB Python vs ~10MB Rust)
- Want single binary distribution

### Consequences
- Fast path to working product
- Familiar technology
- Rich Python ecosystem for data processing
- Bundle includes Python runtime
- Can optimize incrementally
- Rust remains an option for v2 optimization

---

## [DECISION-008] Skill Definition Format

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Skills (like /daily, /wod) need a definition format. Current format is markdown files in .claude/skills/.

### Options Considered
1. **Keep markdown format** - Human readable, familiar
2. **YAML/JSON config** - More structured
3. **Python code** - Full flexibility
4. **Hybrid** - Markdown with frontmatter

### Decision
**Keep markdown format** with structured frontmatter for metadata.

### Consequences
- Easy to create and edit skills
- Claude can read skill definitions directly
- Need parser for frontmatter
- Some skills may need code handlers

---

## Pending Decisions

## [DECISION-009] File Watching Strategy

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Need to decide how aggressively the app should watch for file changes and trigger extraction.

### Options Considered
1. **Watch all files** - Extract on any .md change
2. **Watch only Daily-Notes** - Extract only daily notes folder
3. **Manual trigger only** - User clicks "Extract"
4. **Hybrid** - Auto for Daily-Notes, manual for others

### Decision
**Watch all files** - extract on any .md file change.

### Consequences
- Data always up-to-date
- More API calls (when Claude is enabled)
- Should debounce rapid changes
- May need file/folder exclusion patterns for large vaults
- Consider extraction caching to avoid re-processing unchanged content

---

## [DECISION-010] Single Workspace (No Vault Concept)

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Should the app support multiple vaults/workspaces?

### Options Considered
1. **Single vault only** - One vault per installation
2. **Multiple vaults with switching** - Dropdown to switch
3. **Vault as project concept** - Like VS Code workspaces

### Decision
**Single workspace** - no vault concept. You have one workspace, period.

### Consequences
- Simpler mental model
- Simpler architecture
- No switching UI needed
- Users who need separation can run multiple instances
- Workspace path configured at setup/in settings

---

## [DECISION-011] Sync/Backup via Storage Backend

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
How should users backup and sync their data?

### Options Considered
1. **Git-based** - Users manage their own git repo
2. **Cloud sync** - Dropbox, iCloud, OneDrive
3. **Custom sync service** - Build our own sync
4. **None (local only)** - User's responsibility
5. **Storage backend handles it** - Ties to DECISION-013

### Decision
**Storage backend handles sync/backup** - ties to DECISION-013 (Pluggable Storage Backend).

- v1: Local filesystem only (user handles backup manually or via git)
- Future: Cloud backends (Azure Blob, S3, etc.) handle sync natively
- Users and authentication deferred to later phase

### Consequences
- Simple for v1 - just local files
- Cloud sync comes "free" with storage backend implementation
- No custom sync logic to build
- User auth/login system deferred

---

## [DECISION-012] Licensing Model

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
What licensing model should the project use?

### Options Considered
1. **Open source (MIT/Apache)** - Fully free, anyone can use/modify/sell
2. **Source available** - Code visible but restricted commercial use
3. **Commercial license** - Paid product
4. **Freemium** - Free core, paid features

### Decision
**Source available** - code is publicly visible but commercial use is restricted.

Possible licenses to consider:
- **BSL (Business Source License)** - Converts to open source after time period
- **FSL (Functional Source License)** - Similar to BSL
- **Custom license** - Tailored terms

### Consequences
- Transparency - users can inspect/audit code
- Protection - competitors can't just resell it
- Community contributions possible with CLA
- Need to define exact license terms
- May limit some adoption compared to pure open source

---

## [DECISION-013] Pluggable Storage Backend

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
The app needs file storage for markdown notes and the DuckDB database. While local filesystem is the initial target, users may want cloud storage for sync, backup, or multi-device access.

### Options Considered
1. **Local filesystem only** - Simple, fast, but no sync
2. **Cloud only** - Forces dependency on cloud provider
3. **Pluggable storage abstraction** - Interface with multiple backends

### Decision
**Pluggable storage abstraction** - Build a `StorageBackend` interface that can be implemented for different storage providers:

```python
class StorageBackend(Protocol):
    async def read(self, path: str) -> bytes: ...
    async def write(self, path: str, content: bytes) -> None: ...
    async def delete(self, path: str) -> None: ...
    async def list(self, prefix: str) -> list[str]: ...
    async def exists(self, path: str) -> bool: ...
```

**Planned Implementations:**
| Priority | Backend | Status |
|----------|---------|--------|
| 1 | Local Filesystem | First implementation |
| 2 | Azure Blob Storage | Future |
| 3 | AWS S3 | Future |
| 4 | GCP Cloud Storage | Future |

### Consequences
- Clean separation between app logic and storage
- Can add new backends without changing core code
- Local-first by default, cloud optional
- Need to handle eventual consistency for cloud backends
- DuckDB database stays local (cloud backends sync the .duckdb file)
- Markdown files are the source of truth regardless of storage backend

### Implementation Notes
- Storage backend selection via settings UI
- Credentials stored in system keychain
- File watcher needs per-backend implementation
- Consider WebDAV as a universal protocol option

---

## [DECISION-014] Docker Compose for Local Development

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Need a consistent development environment that can run the Python backend with proper access to local vault files.

### Options Considered
1. **Run Python directly** - Simple but inconsistent environments
2. **Docker Compose** - Containerized, reproducible, easy volume mounts
3. **Local Kubernetes (minikube)** - Full k8s but complex for dev
4. **Dev containers (VS Code)** - IDE-specific

### Decision
**Docker Compose for local development**, with Kubernetes manifests added later when approaching production.

**Development:** `docker-compose up` spins up:
- Python FastAPI backend (port 8000)
- Volume mount for vault directory (read/write)
- Volume mount for DuckDB data directory

**Production path:** Minikube testing before cloud deployment.

### Consequences
- Consistent dev environment across machines
- Volume permissions must be handled (user mapping)
- Hot reload via volume mounts
- Easy to add services (Redis cache, etc.) later
- Can generate k8s manifests from compose later

### Volume Mount Strategy
```yaml
volumes:
  - ${VAULT_PATH:-~/vault}:/app/vault:rw
  - ${DATA_PATH:-~/.unstructured}:/app/data:rw
```

- Uses environment variables with defaults
- `:rw` ensures write access
- User/group mapping for permissions

---

## [DECISION-016] Simplified CSV Storage (Flat Files)

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Original design used date-partitioned CSV folders:
```
data/exercise_log/{yyyy}/{mm}/{dd}/{yyyy}_{mm}_{dd}_exercise_log.csv
```

This adds complexity without benefit at personal data volumes.

### Options Considered
1. **Date-partitioned folders** - Complex, optimized for big data
2. **Flat CSV files** - Single file per data type, DuckDB filters by date
3. **DuckDB only** - No CSV export

### Decision
**Flat CSV files** - one file per data type.

```
data/
├── exercise_log.csv
├── food_log.csv
├── daily_metrics.csv
└── daily_tasks.csv
```

### Consequences
- Simpler file structure
- DuckDB handles date filtering efficiently (~10K rows is trivial)
- Easy to inspect/edit CSVs manually
- Can partition later if data grows significantly
- CSV export still available for portability

---

## [DECISION-017] Haiku for Extraction (Cost Optimization)

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Data extraction from notes to structured JSON is a well-defined task. Using Sonnet or Opus for this is expensive overkill.

### Options Considered
1. **Opus for everything** - Expensive (~$30/month)
2. **Sonnet for everything** - Moderate (~$10/month)
3. **Haiku for extraction, Sonnet for complex** - Cheap (~$1-3/month)

### Decision
**Haiku 4.5 (claude-haiku-4-5-20251001) for extraction and simple tasks.**
Sonnet 4.5 only for complex reasoning when needed.

### Consequences
- ~10x cost reduction for extraction tasks
- Faster API responses (Haiku is quicker)
- May need Sonnet fallback for edge cases
- Monthly costs drop from ~$10 to ~$1-3

---

## [DECISION-018] Real-time Extraction on Save

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Need to decide when data extraction should occur - immediately on save or batched.

### Options Considered
1. **Real-time on save** - Extract immediately with debounce
2. **Batch on demand** - User triggers extraction manually
3. **Hybrid** - Real-time for some folders, manual for others

### Decision
**Real-time extraction on save** with 2-second debounce after last edit.

### Consequences
- Data always up-to-date after saving
- Debounce prevents excessive API calls during rapid edits
- May need optimization for large files
- Batch processing still available on app startup

---

## [DECISION-019] Markdown as Source of Truth (Conflict Resolution)

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
If markdown and DuckDB data disagree, which is authoritative?

### Options Considered
1. **Markdown wins** - DuckDB is derived view
2. **DuckDB wins** - Preserve database edits
3. **Prompt user** - Show diff, let user choose

### Decision
**Markdown always wins** - DuckDB is a derived view that can be fully regenerated.

### Consequences
- Simple mental model
- DuckDB can be deleted and rebuilt anytime
- No manual database edits supported
- Git version control works naturally on markdown

---

## [DECISION-020] Additive Schema Evolution

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
How to handle adding new columns to the schema over time.

### Options Considered
1. **Additive only** - New columns default NULL
2. **Migration scripts** - Versioned schema with migrations
3. **Re-extract everything** - Repopulate on schema change

### Decision
**Additive only** - new columns get NULL for existing records.

### Consequences
- No migration complexity
- Can re-extract historical data if needed
- No breaking changes to existing data
- Simple schema versioning

---

## [DECISION-021] Claude Tool Use for Extraction

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Should extraction use Claude's tool use feature or plain prompting?

### Options Considered
1. **Plain prompting** - Ask for JSON, parse response
2. **Tool use** - Define extraction as tool with schema

### Decision
**Use Claude's tool use** for data extraction.

### Consequences
- Guaranteed JSON schema compliance
- More reliable than plain prompting
- Slightly more complex implementation
- Eliminates JSON parsing errors

---

## [DECISION-022] Streaming Responses

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Should Claude responses stream to the UI or wait for completion?

### Options Considered
1. **No streaming** - Wait for complete response
2. **Streaming** - Show response as it generates

### Decision
**Stream responses** for queries and skill execution.

### Consequences
- Better UX for longer responses
- Extraction does not stream (needs complete JSON)
- Slightly more complex frontend handling

---

## [DECISION-023] Session-based Conversation History

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Should the chat interface maintain conversation history?

### Options Considered
1. **Stateless** - Each query independent
2. **Session history** - Keep context within session
3. **Persistent history** - Store long-term

### Decision
**Session-based history** - cleared on app restart.

### Consequences
- Context maintained during session
- No long-term storage concerns
- Privacy-friendly
- Manageable context window

---

## [DECISION-024] Composite ID Generation

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
How to generate unique IDs for exercise_log records.

### Options Considered
1. **Composite key** - `{activity_id}_{exercise_name}_{set_number}`
2. **UUID** - Random unique identifier
3. **Auto-increment** - Database handles it
4. **Natural key** - No ID column

### Decision
**Composite key pattern**: `{activity_id}_{exercise_name}_{set_number}`
Example: `20260131_str_1_squat_1`

### Consequences
- Deterministic (same content = same ID)
- Human-readable for debugging
- Enables idempotent extraction
- Exercise names must be normalized to snake_case

---

## [DECISION-025] Normalized Table Design

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Should activity metadata be in a separate table or denormalized into exercise_log?

### Options Considered
1. **Normalized** - Separate `activities` table with foreign key
2. **Denormalized** - `activity_type` repeated in each exercise_log row

### Decision
**Normalized design** - separate `activities` and `exercise_log` tables.

### Consequences
- Cleaner data model
- Activity metadata stored once per session
- `exercise_log` references `activity_id` as foreign key
- Demo examples need updating

---

## How to Add Decisions

1. Copy the template at the top
2. Assign next DECISION number
3. Fill in context and options
4. Record the decision and rationale
5. Update status as implementation progresses

---

*Back to: [README.md](./README.md)*
