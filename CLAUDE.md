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

### DuckDB Notes

DuckDB does not support AUTO_INCREMENT. Use `DEFAULT nextval('sequence_name')` or generate IDs in application code. After any DuckDB schema changes, verify with a test insert and query to confirm persistence.

## CSS/UI Changes

When making CSS or layout changes, make ONE change at a time and verify it doesn't regress other styling. Never batch multiple CSS fixes in a single edit. After each change, describe exactly what changed and what it should look like.

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

### Commit Hygiene

When staging files for commit, only stage files directly related to the current task. Use `git add <specific-files>` rather than `git add .` or broad patterns. Double-check staged files with `git diff --cached --stat` before committing.

### Pre-Work Checklist

- [ ] Docker is running: `docker compose -f docker-compose.dev.yml up -d`
- [ ] Tests pass: `cd backend && pytest` + `cd frontend && npm test`
- [ ] Feature branch created: `git checkout -b feature/{name}`
- [ ] Kanban task exists

---

## Brand & Design

For visual identity, colors, typography, and component styling, see the `brand-guidelines` skill.

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

Skills and agents are auto-discovered from `.claude/skills/` and `.claude/agents/`.

**Last Updated**: 2026-02-08
