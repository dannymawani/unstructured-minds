# Codebase Cleanup Plan

**Status:** In Progress
**Created:** 2026-03-13

Comprehensive audit of stale code, unused files, dead functions, and outdated documentation across the entire codebase.

## 1. Architecture / Project Structure

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 1.1 | Delete `landing/` directory | `landing/` | Dead — CI deploys `website/` now |
| 1.2 | Delete `architecture/` root directory | `architecture/diagrams/` | Unreferenced go-live diagrams |
| 1.3 | Delete `um_logo.svg` at project root | `./um_logo.svg` | Duplicate; canonical copies elsewhere |
| 1.4 | Delete `scripts/import_obsidian_data.py` | `scripts/import_obsidian_data.py` | One-time migration, completed |

## 2. Technology Stack

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 2.1 | Remove `@milkdown/theme-nord` from package.json | `frontend/package.json` | Never imported |
| 2.2 | Remove `@tanstack/react-virtual` after FileTree cleanup | `frontend/package.json` | Only used by dead FileTree |

## 3. Frontend Components

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 3.1 | Delete `BacklinksPanel/` | `frontend/src/components/BacklinksPanel/` | Orphaned |
| 3.2 | Delete `TagsPanel/` | `frontend/src/components/TagsPanel/` | Orphaned |
| 3.3 | Delete `Schemas/SchemaManager` | `frontend/src/components/Schemas/` | Orphaned |
| 3.4 | Delete `FileTree.tsx` + `FileTreeItem.tsx` (keep treeUtils) | `frontend/src/components/FileTree/` | Dead in production |
| 3.5 | Remove `sidebarTab` / `setSidebarTab` from useUIState | `hooks/useUIState.ts` | Dead state |
| 3.6 | Remove `handleDeleteFile` / `handleRenameFile` from useFileManager | `hooks/useFileManager.ts` | Never destructured |
| 3.7 | Remove dead CSS classes | `frontend/src/index.css` | Never used |
| 3.8 | Delete unused logo assets | `frontend/public/` | Not referenced |
| 3.9 | Remove `getShortcutDisplay` export | `hooks/useKeyboardShortcuts.ts` | Never imported |
| 3.10 | Remove `buttonVariants` export | `components/ui/button.tsx` | Never imported |

## 4. Backend

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 4.1 | Remove dead logger helpers | `backend/src/logging_config.py` | No production callers |
| 4.2 | Delete test_logging.py | `backend/tests/test_logging.py` | Tests dead functions |
| 4.3 | Remove `include_export_routes()` | `backend/src/api/export.py` | Never called |
| 4.4 | Remove `get_rate_limit_handler()` + `RATE_LIMIT_DEFAULT` | `backend/src/middleware/rate_limit.py` | Never called |
| 4.5 | Remove `get_request_id()` | `backend/src/middleware/request_logging.py` | Never called externally |
| 4.6 | Remove `AnalyticsCacheManager.set_user()` | `backend/src/db/analytics_cache.py` | Never called |
| 4.7 | Remove dead imports: `validate_query_length` | `backend/src/api/search.py`, `query.py` | Never called |
| 4.8 | Clean up middleware `__init__.py` re-exports | `backend/src/middleware/__init__.py` | Exports dead symbols |

## 5. Database

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 5.1 | Remove `file_index` table DDL | `schema.py`, `postgres_schema.py` | Never read/written |
| 5.2 | Remove `progress_reviews` DDL + from CACHE_TABLES | schema files + `analytics_cache.py` | Never used, wastes cache cycles |

## 6. Scripts

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 6.1 | Archive stale scripts (keep backup_to_local.py) | `backend/scripts/` | One-time migrations done |

## 7. Infrastructure

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 7.1 | Fix or remove Dockerfile.dev reference | `docker-compose.dev.yml` | References nonexistent file |
| 7.2 | Fix OG image URL in website | `website/index.html` | Points to unserved path |

## 8. Documentation

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 8.1 | Delete `docs/archive/` | `docs/archive/` | Raw scratch notes, superseded |
| 8.2 | Remove watchdog references from tech-stack | `docs/tech-stack.md` | Unimplemented library |
| 8.3 | Fix data flow diagram in tech-stack | `docs/tech-stack.md` | Shows nonexistent services |
| 8.4 | Remove CONTRIBUTING.md reference from sales.md | `docs/sales.md` | Links to nonexistent file |

## 9. Skills & Agents

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 9.1 | Update `db-analyst` agent — fix schemas | `.claude/agents/db-analyst.md` | Substantially wrong |
| 9.2 | Update `backend-dev` agent — fix file structure | `.claude/agents/backend-dev.md` | Wrong modules |
| 9.3 | Update `frontend-dev` agent — fix dirs, remove Zustand | `.claude/agents/frontend-dev.md` | Wrong deps |
| 9.4 | Update `doc-writer` agent — remove docs/api/ ref | `.claude/agents/doc-writer.md` | Nonexistent dir |
| 9.5 | Update `duckdb-query` skill — fix columns and scales | `.claude/skills/duckdb-query/SKILL.md` | Wrong column names |
| 9.6 | Archive `data-integration` skill | `.claude/skills/data-integration/SKILL.md` | Completed migration |

## 10. Shared Files

| # | Action | File(s) | Impact |
|---|--------|---------|--------|
| 10.1 | Evaluate `shared/schemas/*.json` | `shared/schemas/` | Not loaded at runtime |
