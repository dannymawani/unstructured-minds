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
- Skills and automation scripts

### Key Reference Paths in Obsidian Repo

| What | Path |
|------|------|
| Data schemas | `/Users/dmh/Code/obsedian/data/schemas/` |
| CSV data | `/Users/dmh/Code/obsedian/data/` |
| Python scripts | `/Users/dmh/Code/obsedian/scripts/` |
| Daily notes | `/Users/dmh/Code/obsedian/secondbrain/Daily-Notes/` |
| Templates | `/Users/dmh/Code/obsedian/secondbrain/Templates/` |
| Claude config | `/Users/dmh/Code/obsedian/CLAUDE.md` |

---

## Project Overview

Unstructured Minds transforms natural language notes into structured, queryable data using Claude as the AI extraction layer and DuckDB as the data warehouse.

### Core Flow
```
Markdown Note → Claude Extraction → CSV/DuckDB → Natural Language Query
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19 + Milkdown (pure web app) |
| Backend | Python 3.14 + FastAPI |
| Database | DuckDB 1.4 |
| AI | Claude API (Haiku for extraction, Sonnet for queries) |
| Deployment | Docker Compose |

> **Note:** No Electron - this is a containerized web app for easy deployment and lighter footprint.

## Data Patterns

### Date Format
- **Filenames**: `YYYY-MM-DD` (e.g., `2026-01-31.md`)
- **CSV dates**: `YYYY-MM-DD`
- **Daily note path**: `Daily-Notes/YYYY-MM/YYYY-MM-DD.md`

### CSV Storage Structure
```
data/
├── exercise_log.csv      # Single file per data type
├── food_log.csv          # DuckDB handles filtering by date
├── daily_metrics.csv
├── daily_tasks.csv
└── schemas/*.json
```

> **Simplified:** No date-partitioned folders. DuckDB queries flat CSVs efficiently at personal data volumes.

## Demo Examples

The `demo_examples/` folder contains reference implementations showing:
- Input markdown notes
- Expected extracted CSV data
- Schema definitions

Use these as the ground truth for how extraction should work.

## Implementation Docs

All planning documents are in `/implementation_plan/`:

| Document | Purpose |
|----------|---------|
| 01-VISION.md | Product vision, user stories |
| 02-ARCHITECTURE.md | System design |
| 03-FRONTEND.md | UI/UX specs |
| 04-DATA-LAYER.md | Database design |
| 05-LLM-INTEGRATION.md | Claude integration |
| 06-IMPLEMENTATION.md | Code patterns |
| 07-DECISIONS.md | ADRs |
| 09-IMPLEMENTATION-PLAN-AND-STEPS.md | Build phases |

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

### Background Skills (Auto-loaded by Claude)

These skills provide context automatically when relevant:
- `api-conventions` - FastAPI patterns
- `python-conventions` - Python best practices
- `frontend-patterns` - React/Milkdown patterns
- `extract-data` - Data extraction patterns

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

**Last Updated**: 2026-01-31
