# Performance Review & Roadmap to A+

**Status:** Planning
**Created:** 2026-03-13
**Current Grade:** B overall

## Current Grades

| Area | Grade | Summary |
|------|-------|---------|
| Architecture | A- | Clean two-mode design, good separation of concerns |
| Security | B+ | Strong SQL defense, CSP could be tighter |
| Frontend perf | B | Good splitting strategy, editor bundle too eager |
| Backend perf | B+ | DuckDB is fast, some query batching opportunities |
| Test coverage | B- | 40% ratio, 4 modules untested |
| Infrastructure | C+ | Good Docker setup, no CI/CD pipeline |
| Code quality | B | Consistent patterns, dashboard needs splitting |

---

## Architecture: A- → A+

**What's already good:** Two-mode local/cloud design, DI system, storage abstraction, clean project structure.

**To reach A+:**

1. **Split `dashboard.py` (1,830 lines → 5 modules)**
   - `dashboard/summary.py` — KPIs, streak, counts
   - `dashboard/strength.py` — exercise progress, exercise table
   - `dashboard/endurance.py` — endurance log, endurance progress
   - `dashboard/nutrition.py` — calorie/macro aggregates
   - `dashboard/trends.py` — heatmap, sleep trends, mood correlation, metrics trends, body weight
   - Keep a `dashboard/__init__.py` that assembles the router
   - Estimated effort: Medium (refactor, no new features)

2. **Consolidate the 9 duplicate `get_db` definitions**
   - Modules define their own `get_db` instead of using `dependencies.get_db`
   - Root cause: `dashboard.py` needs a local `get_db` that ties auth + cache seeding together (documented in ai_docs/04)
   - Solution: Make the shared `get_db` in `dependencies.py` handle both cases, remove per-module copies
   - Estimated effort: Medium (requires careful testing of cloud mode)

3. **Standardize sync/async handler pattern**
   - Decision: sync `def` for DuckDB-only endpoints (FastAPI threadpools them), `async def` for endpoints calling external services (Claude API, Postgres, file I/O)
   - Document the rule in `api-conventions` skill
   - Estimated effort: Low (mostly a convention decision + small refactors)

---

## Security: B+ → A+

**What's already good:** 4-layer SQL validation, read-only transaction wrapping, parameterized queries, rate limiting, Clerk JWT auth, path traversal prevention.

1. **Tighten CSP — remove `unsafe-inline` and `unsafe-eval`**
   - `unsafe-eval` is likely required by Milkdown/ProseMirror — investigate if newer versions have removed this need
   - `unsafe-inline` for scripts: replace with nonce-based CSP (`'nonce-{random}'` per request, injected into `<script>` tags)
   - `unsafe-inline` for styles: may be unavoidable with Tailwind's runtime styles, but investigate `style-src` with hashes
   - Estimated effort: High (requires Milkdown/Clerk compatibility testing)

2. **Add `USER nginx` to frontend Dockerfile**
   - One-line fix: add `USER nginx` before `CMD`
   - Estimated effort: Trivial

3. **Add `.dockerignore` files**
   - Backend: ignore `.git`, `tests/`, `__pycache__/`, `*.md`, `.env`
   - Frontend: ignore `.git`, `node_modules/`, `*.md`, `.env`
   - Prevents secrets leaking into build context and speeds up builds
   - Estimated effort: Trivial

4. **Enable HSTS when SSL is configured**
   - Uncomment the HSTS header in `security-headers.conf` once TLS is set up
   - Estimated effort: Trivial (when SSL is ready)

---

## Frontend Performance: B → A+

**What's already good:** 3 vendor chunks, 3 lazy routes, gzip, immutable caching, useMemo/useCallback usage.

1. **Lazy-load the Editor (biggest single win)**
   - Milkdown is 570 kB (181 kB gzipped) — ~50% of total JS
   - Currently in the main `index` chunk, loaded on every page
   - Wrap the Editor view in `React.lazy()` like Dashboard/Kanban/Calendar already are
   - Expected impact: Initial bundle drops from 363 kB → ~180 kB gzipped
   - Estimated effort: Low

2. **Add `React.memo` to callback-receiving components**
   - 65+ `useCallback` calls exist but zero `React.memo` wrappers
   - Without `React.memo`, `useCallback` is pure overhead (stable reference but child re-renders anyway)
   - Priority targets: `PersonalTaskCard`, `FileTreeItem` (if revived), `ChatMessage`, `DashboardSummary`, all widget components
   - Estimated effort: Low-Medium (wrap components, verify no bugs)

3. **Lazy-load more component groups**
   - Currently lazy: Dashboard, KanbanBoard, CalendarView (3 of 19)
   - Should also lazy-load: Chat, Settings, QuickCapture, DailyNoteWizard, TemplatePicker, Onboarding
   - These are modals/panels that aren't needed at initial render
   - Estimated effort: Low

4. **Extract state from App.tsx monolith**
   - App.tsx is 389 lines managing all state — any state change re-renders the entire tree
   - Options:
     a. Context providers for each domain (files, UI, theme) — already partially done with hooks
     b. Zustand for truly global state (lightweight, no boilerplate)
     c. At minimum, split the Editor view into its own component with colocated state
   - Estimated effort: Medium-High

5. **Reduce Milkdown chunk size**
   - Investigate tree-shaking: are all ProseMirror plugins needed?
   - Check if `@milkdown/kit` bundles more than what's used
   - Consider dynamic import of GFM/history plugins only when editor mounts
   - Estimated effort: Medium (requires Milkdown API investigation)

---

## Backend Performance: B+ → A+

**What's already good:** DuckDB columnar analytics, 14 indexes, connection pooling, TTL caching, rate limiting.

1. **Batch dashboard summary queries**
   - Currently: 7-8 serial `db.execute()` calls in `get_dashboard_summary`
   - Fix: Combine into 1-2 CTE queries returning multiple aggregates
   - Expected impact: ~4-6x fewer DB round-trips for the most-called endpoint
   - Estimated effort: Medium

2. **Fix N+1 in `bulk_complete_tasks`**
   - Currently: 2 queries per task in a loop (update + re-fetch)
   - Fix: Single `UPDATE ... WHERE id IN (...)` + single `SELECT` to return updated rows
   - Estimated effort: Low

3. **Batch analytics cache refresh**
   - Currently: row-by-row `INSERT` in a loop for each table
   - Fix: Use `executemany()` or `INSERT INTO ... SELECT` with parameter batches
   - Expected impact: Faster cache refresh, less GIL contention
   - Estimated effort: Low

4. **Add explicit pagination to remaining dashboard endpoints**
   - Currently bounded by `days` param (max 365), but no row-level pagination
   - Add optional `limit`/`offset` with sensible defaults
   - Estimated effort: Low

---

## Test Coverage: B- → A+

**What's already good:** 26 test files, 6,144 lines, covers critical paths (extraction, queries, security, storage).

1. **Add tests for untested modules**
   - `calendar.py` — test month data aggregation, workout suggestions
   - `chat.py` — test SSE streaming, message handling
   - `kanban.py` — test CRUD, task ordering, update notes
   - `note_assist.py` — test multimodal note editing flow
   - Estimated effort: Medium (4 new test files)

2. **Increase test:source ratio from 0.40 to 0.60+**
   - Priority: dashboard endpoints (1,830 lines, only 451 lines of tests)
   - Add edge case tests for date boundaries, empty data, pagination
   - Estimated effort: Medium

3. **Add frontend component tests**
   - Currently: only FileTree had tests (now deleted)
   - Priority targets: Dashboard widgets (data transformation logic), useFileManager (save/autosave flow), apiClient (token gating)
   - Estimated effort: Medium-High

4. **Add integration test for extraction pipeline end-to-end**
   - Markdown in → Claude mock → DB rows out → Dashboard query → correct results
   - Validates the full data flow documented in ai_docs/07
   - Estimated effort: Medium

---

## Infrastructure: C+ → A+

**What's already good:** Multi-stage Docker builds, nginx reverse proxy, health checks, rate limiting, security headers.

1. **Add CI/CD pipeline (highest priority)**
   - GitHub Actions workflow:
     - On PR: run `pytest`, `npm test`, `npm run typecheck`, `ruff check`
     - On merge to main: build Docker images, push to registry
     - Optional: deploy to staging on merge
   - Estimated effort: Medium

2. **Add `.dockerignore` files**
   - See Security section item 3
   - Estimated effort: Trivial

3. **Add resource limits to docker-compose.yml**
   - Backend: `mem_limit: 1g`, `cpus: '1.0'`
   - Frontend: `mem_limit: 256m`, `cpus: '0.5'`
   - Prevents runaway processes from taking down the host
   - Estimated effort: Trivial

4. **Fix backend Dockerfile layer caching**
   - Current: `pip install .` with hatchling requires source at install time, busting cache on every code change
   - Fix: Export dependencies to `requirements.txt` in CI, `COPY requirements.txt` + `pip install -r requirements.txt` first, then `COPY src/` + `pip install --no-deps .`
   - Estimated effort: Low

5. **Add `USER nginx` to frontend Dockerfile**
   - See Security section item 2
   - Estimated effort: Trivial

---

## Code Quality: B → A+

**What's already good:** Consistent DI, Pydantic everywhere, parameterized SQL, structured logging (where present).

1. **Add logging to all API modules**
   - 15 of 18 modules have zero logging
   - At minimum: log errors, log slow queries (>1s), log Claude API calls
   - Use structlog consistently (already configured)
   - Estimated effort: Medium

2. **Reduce broad `except Exception` catches**
   - 51 instances across the codebase
   - Audit each: replace with specific exceptions where possible
   - Keep broad catches only for truly optional/fallback code paths, but always log the exception
   - Estimated effort: Medium

3. **Centralize Pydantic models**
   - Currently inline in route files
   - Move shared response models to `api/models/` or `api/schemas.py`
   - Keep request models colocated with their endpoints
   - Estimated effort: Medium

4. **Document the sync/async convention**
   - Add to `api-conventions` skill and `ai_docs/05-backend.md`
   - Rule: sync for DuckDB-only, async for external I/O
   - Estimated effort: Trivial

---

## Priority Roadmap

### Phase 1: Quick Wins (1-2 sessions)
- [ ] Lazy-load Editor component (frontend perf biggest win)
- [ ] Add `.dockerignore` files
- [ ] Add `USER nginx` to frontend Dockerfile
- [ ] Add resource limits to docker-compose.yml
- [ ] Fix N+1 in `bulk_complete_tasks`
- [ ] Batch analytics cache INSERT operations

### Phase 2: CI/CD + Testing (2-3 sessions)
- [ ] Create GitHub Actions CI workflow (pytest + typecheck + lint)
- [ ] Add tests for calendar, chat, kanban, note_assist
- [ ] Add frontend component tests for Dashboard widgets
- [ ] Increase backend test coverage to 0.60+ ratio

### Phase 3: Refactoring (3-4 sessions)
- [ ] Split dashboard.py into sub-modules
- [ ] Consolidate duplicate `get_db` definitions
- [ ] Add logging to all 15 unlogged API modules
- [ ] Batch dashboard summary into CTE queries
- [ ] Add `React.memo` to callback-receiving components
- [ ] Lazy-load Chat, Settings, QuickCapture, DailyNoteWizard

### Phase 4: Polish (2-3 sessions)
- [ ] Tighten CSP (investigate nonce-based, remove unsafe-eval)
- [ ] Extract state from App.tsx monolith
- [ ] Centralize Pydantic models
- [ ] Audit and reduce broad exception catches
- [ ] Fix backend Dockerfile layer caching
- [ ] Add integration test for extraction pipeline
- [ ] Investigate Milkdown tree-shaking opportunities

### Target: All A+ after Phase 4
