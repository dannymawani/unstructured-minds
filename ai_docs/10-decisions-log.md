# Decisions Log

Architecture Decision Records (ADR) for Unstructured Minds. Append-only — newest entries at the bottom.

---

### 2025-01: No AUTO_INCREMENT in DuckDB

**Context:** DuckDB doesn't support AUTO_INCREMENT syntax.
**Decision:** Use `DEFAULT nextval('seq')` for auto-incrementing columns or generate IDs in application code.
**Alternatives:** UUID generation, custom sequence tables.
**Outcome:** All ID generation uses either sequences or deterministic ID formats (e.g., `{YYYYMMDD}_{type}_{index}`).

### 2025-01: Prepared Statements Disabled for Postgres

**Context:** PgBouncer/Supavisor compatibility issues with prepared statements.
**Decision:** Disable prepared statements in the psycopg connection pool.
**Alternatives:** Direct connection without pooler, named prepared statements.
**Outcome:** Compatible with Neon's connection pooler (Supavisor).

### 2025-01: dashboard.py Local get_db Before Endpoints

**Context:** Python evaluates `Depends()` default argument values at function definition time.
**Decision:** The local `get_db` function in `dashboard.py` (which depends on `get_user_id` for auth + cache seeding) must be defined before all endpoint functions in the file.
**Alternatives:** None — this is a Python language constraint.
**Outcome:** Documented as a critical ordering requirement. Moving endpoint definitions above `get_db` would silently break user isolation in cloud mode.

### 2025-01: Global Fetch Interceptor for Auth

**Context:** 50+ direct `fetch()` calls across 28 frontend components needed auth headers.
**Decision:** Patch `window.fetch` globally to inject `Authorization: Bearer` header for all API calls.
**Alternatives:** Wrapping each call in an auth-aware helper, using axios interceptors.
**Outcome:** Zero migration effort for existing fetch calls. All API calls automatically authenticated.

### 2025-01: uuid5 for User IDs

**Context:** Needed deterministic mapping from Clerk's string subject IDs to UUIDs for Postgres.
**Decision:** Use `uuid5(NAMESPACE_URL, clerk_sub)` for a deterministic Clerk sub → UUID mapping.
**Alternatives:** Storing Clerk sub as VARCHAR, using uuid4 with lookup table.
**Outcome:** Same Clerk user always maps to same UUID. No lookup table needed.

### 2025-01: CSP in One File

**Context:** Nginx doesn't inherit `add_header` from parent when child uses `add_header`.
**Decision:** Put all security headers in `nginx/security-headers.conf`, `include`d in both server block and `location = /index.html`.
**Alternatives:** Duplicating headers in each location block.
**Outcome:** Single source of truth for CSP. Update one file only.

### 2025-01: VITE_CLERK_PUBLISHABLE_KEY as Build Arg

**Context:** Vite bakes `VITE_*` variables into the JS bundle at build time (not available at runtime).
**Decision:** Pass `VITE_CLERK_PUBLISHABLE_KEY` as a Docker build arg, not runtime env.
**Alternatives:** Runtime config injection via `window.__CONFIG__`.
**Outcome:** Dockerfile warns when empty. Local mode works without it.

### 2025-01: Defense-in-Depth for AI-Generated SQL

**Context:** Natural language → SQL via Claude is inherently risky for prompt injection.
**Decision:** 4-layer defense: system prompt separation, `validate_sql()` (deny-lists + DuckDB parser), `read_only_execute()` (BEGIN/ROLLBACK), auto LIMIT 100.
**Alternatives:** Allowlisting specific query patterns, using an ORM.
**Outcome:** Even if Claude generates malicious SQL, it cannot modify data or access system tables.

### 2025-03: AI Documentation Wiki (ai_docs/)

**Context:** Documentation scattered across 20 skill files, 8 agents, 7+ doc files, and CLAUDE.md. No structured way for Claude to drill deeper without reading multiple files.
**Decision:** Create `ai_docs/` — a centralized, numbered wiki with 11 docs organized from architecture overview to specific implementation details. Added librarian agent and ai-docs skill for navigation.
**Alternatives:** Expanding CLAUDE.md, restructuring skills as docs, using external wiki.
**Outcome:** CLAUDE.md becomes a lean routing table (~80 lines). Deep documentation accessible via index → specific doc. Librarian agent enables query-driven lookup.
