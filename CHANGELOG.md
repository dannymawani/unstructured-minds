# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
