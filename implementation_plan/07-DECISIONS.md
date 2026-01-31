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

## [DECISION-003] Claude as Intelligence Layer

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Need an LLM for data extraction, query understanding, and skill execution. Options include Claude API, OpenAI, local models.

### Options Considered
1. **Claude API** - Anthropic's hosted service
2. **OpenAI API** - GPT-4, etc.
3. **Local LLM** - Ollama, llama.cpp
4. **Hybrid** - Claude primary, local fallback

### Decision
**Claude API as primary**, with architecture that allows future local model integration.

### Consequences
- Requires internet connection for full functionality
- Monthly API costs (~$10-30 based on usage)
- High quality extraction and reasoning
- Need to handle API errors gracefully
- Should cache responses where possible

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

## [DECISION-005] React + TipTap for Frontend

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Need to choose frontend framework and markdown editor.

### Options Considered
1. **React + TipTap** - Popular framework, best WYSIWYG editor
2. **Svelte + Milkdown** - Smaller bundle, good editor
3. **Vue + TipTap** - Alternative framework
4. **Solid + CodeMirror** - Performance focused
5. **Flutter** - Cross-platform with Dart

### Decision
**React 19.2 + TipTap 3.15** for ecosystem maturity and TipTap's excellent markdown support.

Flutter was rejected because:
- Requires learning Dart (different language)
- Can't reuse web knowledge (React, TypeScript)
- Markdown editors are less mature than TipTap
- Desktop support is newer/less polished than mobile

### Consequences
- Large ecosystem of components
- TipTap has learning curve but excellent docs
- Best-in-class markdown WYSIWYG editing
- Easy to find developers/resources

---

## [DECISION-006] Electron for Desktop

**Date:** 2026-01-31
**Status:** Accepted
**Deciders:** Danny

### Context
Need to decide on application packaging strategy for desktop distribution.

### Options Considered
1. **Tauri** - Rust backend, native webview, small bundle (15-30MB)
2. **Electron** - Node backend, bundled Chromium, large bundle (150-200MB)
3. **Flutter** - Dart, custom rendering engine
4. **Web app only** - No packaging, browser-based

### Decision
**Electron 40.0.0** for desktop packaging.

Reasons:
- TipTap works perfectly (this is critical)
- Easier Python sidecar integration (same Node runtime)
- Battle-tested (Obsidian, VS Code, Slack use it)
- Consistent rendering across platforms
- Larger community and more resources

Tauri rejected because:
- Rust learning curve
- Webview inconsistencies across platforms
- More complex Python integration

Flutter rejected because:
- No TipTap (would need inferior markdown editor)
- Desktop is secondary focus for Flutter
- Different language/paradigm

### Consequences
- Larger bundle size (~150-200MB) - acceptable for desktop app
- Higher memory usage than Tauri
- Easy Python backend integration
- Consistent behavior across macOS, Windows, Linux
- Proven architecture (Obsidian uses same stack)

---

## [DECISION-007] Keep Existing Python Scripts

**Date:** 2026-01-31
**Status:** Proposed

### Context
Existing Python scripts handle extraction, skills, and data processing. Should we rewrite in Rust/TypeScript or wrap existing code?

### Options Considered
1. **Wrap in FastAPI** - Expose existing scripts via API
2. **Rewrite in Rust** - Performance, single binary
3. **Rewrite in TypeScript** - Same language as frontend
4. **Hybrid** - Critical paths in Rust, logic in Python

### Decision
**Wrap existing Python scripts** in FastAPI for POC. Consider Rust rewrite for performance-critical paths later.

### Consequences
- Fast path to working product
- Familiar technology
- Sidecar process management needed
- Bundle includes Python runtime
- Can optimize incrementally

---

## [DECISION-008] Skill Definition Format

**Date:** 2026-01-31
**Status:** Proposed

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

### [DECISION-009] File Watching Strategy

**Options:**
- Watch all files, extract on change
- Watch only Daily-Notes
- Manual trigger only

**To decide:** How aggressive should auto-extraction be?

---

### [DECISION-010] Multi-Vault Support

**Options:**
- Single vault only
- Multiple vaults with switching
- Vault as project concept

**To decide:** Should v1 support multiple vaults?

---

### [DECISION-011] Sync/Backup Strategy

**Options:**
- Git-based (existing)
- Cloud sync (Dropbox, iCloud)
- Custom sync service
- None (local only)

**To decide:** How should users backup/sync data?

---

### [DECISION-012] Licensing Model

**Options:**
- Open source (MIT/Apache)
- Source available
- Commercial license
- Freemium

**To decide:** What's the business model if this becomes a product?

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

## How to Add Decisions

1. Copy the template at the top
2. Assign next DECISION number
3. Fill in context and options
4. Record the decision and rationale
5. Update status as implementation progresses

---

*Back to: [README.md](./README.md)*
