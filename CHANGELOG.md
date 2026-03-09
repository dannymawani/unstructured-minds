# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Landing page redesigned with realistic app mockups (editor, dashboard, heatmap, kanban, chat)
- Endurance table uses SQL-level pagination instead of Python-side sorting and slicing
- Insights endpoint consolidates 5 DB queries into 3 using UNION ALL CTEs
- Move function-level `import re` and `import json` to module-level in dashboard.py
- Add mtime-based cache to `_load_json_config` to avoid repeated disk reads

### Removed
- Remove LifeProfile section entirely (backend API, frontend components, tests, docs)

## [v0.9.0] - 2026-03-09

### Added
- Auto-label new exercises with muscle groups via Claude AI when first encountered during extraction
- Enhanced exercise table with PR detection, trend arrows, muscle group tags, and expandable per-set details
- Muscle group heatmap widget with interactive SVG body map showing training distribution
- Per-set extraction for strength exercises with individual weight/rep tracking
- Endurance tracking system with pace, distance, and heart rate logging
- Unified chat experience combining note-assist and data query modes
- Daily note wizard redesign with improved flow and template selection
- Azure infrastructure setup with Terraform IaC for Container Apps, ACR, and Postgres

### Changed
- Exercise name normalization now restores original names from user notes
- Database schema normalized for per-set exercise data storage

### Fixed
- Fix React reconciliation issues in ExerciseTable with keyed Fragments
- Remove unused BODY_OUTLINE constant from MuscleGroupMap
- Fix duplicate `@staticmethod` decorator that could crash extraction pipeline import
- Fix DuckDB cursor leak — `execute()` now materializes results and closes cursors immediately
- Remove dead `exercise_definitions.json` disk reads from 3 dashboard endpoints
- Remove `console.log` stubs from production Dashboard event handlers
- Fix time-dependent test failure in `test_hide_old_done_tasks`

### Security
- Add auth guards to `/insights/daily`, `/insights/weekly`, `/insights/dismiss` endpoints (previously unauthenticated)
- Add auth guards to `/metrics` and `/metrics/reset` endpoints (previously unauthenticated)
- Remove leaked exercise definitions disk I/O from unauthenticated request paths

## [v0.8.1] - 2026-02-16

### Security
- Harden `/query/natural` endpoint with defense-in-depth against SQL injection, prompt injection, and unauthorized writes
- Add `read_only_execute()` to DatabaseManager — wraps AI-generated SQL in BEGIN/ROLLBACK to prevent writes
- Add DuckDB parser validation, file I/O function deny-list, and system table blocking to `validate_sql()`
- Move SQL generation rules to system prompt to resist prompt injection overrides
- Add automatic LIMIT safety net for unbounded queries
- Add INVALID_QUERY handling for non-data questions

### Added
- Add onboarding system with demo data for new users
- Add go-live architecture diagrams (drawio, PNG, SVG)

## [v0.8.0] - 2026-02-13

### Added
- Add task rollover to daily note wizard — carry forward incomplete tasks from the last 14 days with deadline-aware formatting, auto-select for overdue/in-progress tasks, and immediate source_file sync
- Add nutrition tracking tile to dashboard with calorie and macro breakdowns
- Add mood correlation chart comparing mood against sleep, energy, and exercise

### Changed
- Redesign activity heatmap with improved layout and week number labels
- Improve weekly activity chart with stacked exercise categories

## [v0.7.0] - 2026-02-13

### Added
- Add Clerk authentication (opt-in, no breaking changes)
- Add user data isolation for multi-tenant support
- Add two-mode architecture (local DuckDB / cloud Postgres)
- Add explicit USE_CLOUD flag to toggle local vs Postgres mode
- Add shared community exercise pool with anonymous contributions

### Changed
- Simplify auth to two clean modes (local vs cloud)

### Removed
- Remove unused dependencies, S3 code, and stale docs

## [v0.6.0] - 2026-02-10

### Added
- Add AI exercise name normalization with cached classification
- Add fuzzy exercise name matching for canonical normalization
- Add table insert button and table editing controls to toolbar
- Add sortable columns to exercise table
- Add notes field to personal tasks
- Implement next_steps improvements across dashboard, profile, and extraction
- Sidebar optimizations — configurable folders, drag-drop, rename UX
- Modernize editor styling and optimize bundle splitting

### Fixed
- Use filename date instead of Claude-hallucinated dates for tasks
- Normalize exercise names via fuzzy matching in exercise table
- Enable interactive table editing with Milkdown tableBlock
- Prevent hallucinated insights when database has no data
- Prevent year selector from overlapping heatmap stats text
- Remove hours total from activity heatmap header
- Rebuild workout suggestion with progressive overload
- Exclude non-date files from last daily note query
- Resolve 6 dashboard bugs from testing round
- Migrate daily notes, add month name toggle, improve drag-drop
- Use vault template for daily notes and remove Obsidian syntax

## [v0.5.0] - 2026-02-07

### Added
- Add daily note wizard for structured note creation
- Add file deletion via right-click context menu
- Add file rename via right-click context menu
- Add life profile view with goals, training, and progress reviews
- Add bulk-complete endpoint and /clear-tasks skill

### Changed
- Track vault templates in git

## [v0.4.0] - 2026-02-06

### Added
- Add note-aware chat below editor with image support
- Add React Router for URL-based navigation and deep linking
- Add POST /extract/all SSE endpoint for bulk re-extraction
- Design refresh - Notion/Material-inspired theme overhaul

### Changed
- Remove general chat mode, keep note assist and data query

### Fixed
- Fix note-assist updates not persisting to disk
- Fix task daily note link and add category editor to task modal
- Fix duplicate tasks created when re-saving old notes
- Unify daily note template and deepen Claude note-assist integration
- Make dark theme the default to prevent white flash
- Remove Google Fonts link that broke Vite HTML parser
- Prevent duplicate tasks on re-extraction and startup

## [v0.3.0] - 2026-02-05

### Added
- Add drag-and-drop task movement and status update notes to kanban
- Add year/month hierarchy for Daily-Notes in sidebar
- Connect daily notes tasks to kanban via Personal Tasks tab
- Add optional deadline field to kanban tasks
- Add task detail modal with editable description, deadlines, and daily note link
- Remove personal notes and scratch files from git tracking

### Changed
- Rename kanban statuses to backlog/in_progress/done/cancelled and auto-hide old resolved tasks
- Change kanban deadline from VARCHAR to DATE to match tasks schema

### Fixed
- Fix kanban UX: clickable cards, auto-hide old tasks, remove Implementation tab and date filters
- Fix task card clicks with drag handle and backfill completed_at from task date
- Fix drag-and-drop and click on task cards, correct completed_at backfill
- Use mouse events for task card click detection to avoid dnd-kit conflict
- Switch to editor view when clicking a task card from kanban

## [v0.2.0] - 2026-02-04

### Added
- Add data import functionality
- Expand duckdb-query skill with task schemas and examples
- Add sequence for extraction_log auto-increment id

### Changed
- Replace recharts with pure CSS/SVG charts and fix Dashboard test OOM
- Replace floating tooltip toolbar with fixed top editor toolbar
- Update CLAUDE.md to document JSON config files alongside DuckDB
- Update CLAUDE.md to remove stale scripts references

### Fixed
- Fix TypeScript build errors and plugin relative import failure
- Fix frontend API routing in Docker by setting VITE_API_URL=/api
- Fix rate limiter bugs, layout overflow, editor styles, caching, and test suite
- Fix autosave firing on every keystroke instead of 60s interval
- Fix DuckDB thread safety, dashboard null safety
- Fix editor re-creating on keystroke, schema loading, and Claude API
- Fix slash menu always visible and editor overflow issues
- Fix .env loading, compact layout, kanban task creation, and file click bug

### Removed
- Remove unused plugin, webhook, file watcher systems and clean up artifacts
- Remove unused data files, demo_examples, and existing_data directories

## [v0.1.0] - 2026-02-03

### Added
- Complete Phase 6 & 7: Skills, data integration, editor UX, task system, DuckDB kanban
- Merge feature/extraction-performance branch
- Restore exercise, training, and injury config files

### Fixed
- Merge pull request #1 from dannymawani/feature/extraction-performance

## [v0.0.1] - 2026-02-01

### Added
- Init2 - Initial project setup

---

## Notes

- **v0.1.0** represents the completion of core functionality including backend, frontend, editor, vault, chat, extraction, skills, data integration, editor UX, task system, and DuckDB kanban.
- **v0.2.0** focuses on stabilization, fixing critical bugs in TypeScript compilation, API routing, rate limiting, and performance issues.
- **v0.3.0** introduces the kanban task management system with drag-and-drop, status management, and integration with daily notes.
- **v0.4.0** adds advanced task workflows, note-aware chat, React Router navigation, and a complete design refresh with dark theme defaults.
- **v0.5.0** introduces the daily note wizard for structured note creation, improved file management, and the life profile view for tracking goals and progress.
- **v0.6.0** adds AI-powered exercise normalization, table editing controls, sidebar optimizations, and fixes across dashboard, tasks, and insights.
- **v0.7.0** introduces cloud architecture with two-mode operation (local/cloud), Clerk authentication, user data isolation for multi-tenancy, and a shared community exercise pool.
- **v0.8.x** adds onboarding, security hardening for natural language queries, and go-live architecture diagrams.
- **v0.9.0** introduces AI-powered exercise auto-labeling, muscle group heatmap, per-set tracking, endurance logging, Azure IaC, and a security audit fixing unauthenticated endpoints and cursor leaks.
