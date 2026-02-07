# Unstructured Minds - Development Guide

## Reference Implementation

**For function clarification and data patterns, refer to the working Obsidian repo:**
```
/Users/dmh/Code/obsedian
```

This repo contains the original working implementation of:
- Data extraction from markdown notes
- CSV storage patterns and schemas
- Daily note workflows
- Skills and automation

### Key Reference Paths in Obsidian Repo

| What | Path |
|------|------|
| Data schemas | `/Users/dmh/Code/obsedian/data/schemas/` |
| CSV data | `/Users/dmh/Code/obsedian/data/` |
| Daily notes | `/Users/dmh/Code/obsedian/secondbrain/Daily-Notes/` |
| Templates | `/Users/dmh/Code/obsedian/secondbrain/Templates/` |
| Claude config | `/Users/dmh/Code/obsedian/CLAUDE.md` |

---

## Project Overview

Unstructured Minds transforms natural language notes into structured, queryable data using Claude as the AI extraction layer and DuckDB as the data warehouse.

### Core Flow
```
Markdown Note → Claude Extraction → DuckDB → Natural Language Query
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19 + Milkdown (pure web app) |
| Backend | Python >=3.12 + FastAPI |
| Database | DuckDB 1.4 |
| AI | Claude API (Haiku 4.5 for extraction, Sonnet 4.5 for queries) |
| Deployment | Docker Compose |

> **Note:** No Electron - this is a containerized web app for easy deployment and lighter footprint.

## Data Patterns

### Date Format
- **Filenames**: `YYYY-MM-DD` (e.g., `2026-01-31.md`)
- **CSV dates**: `YYYY-MM-DD`
- **Daily note path**: `Daily-Notes/YYYY-MM/YYYY-MM-DD.md`

### Data Storage Structure
```
data/
├── unstructured.duckdb           # Main database (all extracted data)
├── settings.json                 # User preferences
├── schemas/*.json                # Schema definitions for extraction
├── exercise_definitions.json     # Exercise name aliases and muscle groups
├── training_config.json          # Athlete profile, recovery targets
└── injury_config.json            # Active injuries and constraints
```

> **Note:** Extracted data lives in DuckDB tables. Config/reference files (exercise definitions, training profile, injuries) stay as JSON for easy hand-editing and git tracking.

## Development Workflow

### Mandatory Process

Every feature or change follows this sequence:

```
Plan → Approve → Implement → Test → Review → Deploy
```

1. **Plan** — Create kanban task, write description + acceptance criteria, use plan mode for non-trivial features
2. **Approve** — Review plan before writing code, confirm scope
3. **Implement** — Create `feature/{name}` branch, write focused commits, no direct commits to `main`
4. **Test** — Run `/test` before committing, add tests for new functionality
5. **Review** — Run `/code-review` before merging
6. **Deploy** — Merge to `main`, move kanban task to `done/`, verify Docker

### Branching Rules

- **Never commit directly to `main`** — always use feature branches
- Branch names: `feature/{name}` for features, `fix/{issue}` for bugfixes
- One feature per branch, rebase on main before merging

### Pre-Work Checklist

- [ ] Docker is running: `docker compose -f docker-compose.dev.yml up -d`
- [ ] Tests pass: `cd backend && pytest` + `cd frontend && npm test`
- [ ] Feature branch created: `git checkout -b feature/{name}`
- [ ] Kanban task exists

---

## Brand & Design

For visual identity, colors, typography, and component styling, see:
- **`docs/DESIGN_MANUAL.md`** — Full design system document (generated via `/design-manual`)
- **`brand-guidelines` skill** — Quick reference for colors, fonts, CSS variables

### Quick Color Reference

| Color | Hex | Usage |
|-------|-----|-------|
| Teal | `#14b8a6` | Primary accent, CTAs |
| Dark | `#0f172a` | Text, dark backgrounds |
| Light | `#f8fafc` | Light backgrounds |
| Amber | `#f59e0b` | Warnings, highlights |
| Indigo | `#6366f1` | Links |
| Rose | `#f43f5e` | Errors, destructive |

---

## Skills & Agents

### Available Skills (Slash Commands)

| Skill | Command | Description |
|-------|---------|-------------|
| Code Review | `/code-review` | Review code for quality, security, and conventions |
| Commit | `/commit` | Create well-structured git commits |
| Test | `/test` | Run backend and frontend tests |
| DuckDB Query | `/duckdb-query` | Query the database for insights |
| Fix Issue | `/fix-issue #123` | Fix a GitHub issue by number |
| PR Summary | `/pr-summary #123` | Summarize a PR for review |
| Daily Note | `/daily-note` | Create a daily note from template |
| Design Manual | `/design-manual` | Generate/update DESIGN_MANUAL.md |

### Background Skills (Auto-loaded by Claude)

These skills provide context automatically when relevant:
- `api-conventions` - FastAPI patterns
- `python-conventions` - Python best practices
- `frontend-patterns` - React/Milkdown patterns
- `extract-data` - Data extraction patterns
- `brand-guidelines` - Project colors, typography, CSS variables, logo concept
- `data-integration` - Migration from date-partitioned CSVs to flat DuckDB tables
- `performance-optimization` - Three-tier save model (autosave/Cmd+S/navigation)
- `editor-ux` - Template discoverability, WYSIWYG toolbar, autosave, raw toggle
- `task-integration` - Personal task kanban, two-way markdown sync, task API
- `dev-workflow` - Mandatory plan/approve/test/deploy process, branching rules

### Custom Agents

| Agent | When to Use |
|-------|-------------|
| `code-reviewer` | After writing code, before commits (proactive) |
| `frontend-dev` | React/TypeScript implementation |
| `backend-dev` | Python/FastAPI implementation |
| `db-analyst` | DuckDB queries and data analysis |
| `debugger` | Errors, test failures, unexpected behavior |
| `test-runner` | After writing code to run tests |
| `doc-writer` | Technical docs and API documentation |

### Agent Collaboration Patterns

**Development Workflow:**
1. Write code → `backend-dev` or `frontend-dev`
2. Review changes → `code-reviewer` (proactive)
3. Run tests → `test-runner`
4. Debug failures → `debugger`
5. Commit → `/commit`

**Code Review Flow:**
1. Create PR → use `/pr-summary #123`
2. Review code → `code-reviewer`
3. Address feedback → appropriate dev agent

**Data Analysis:**
1. Query data → `/duckdb-query "question"`
2. Complex analysis → `db-analyst`

---

**Last Updated**: 2026-02-07
