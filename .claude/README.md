# Claude Code Configuration

This directory contains AI agent and skill definitions for [Claude Code](https://claude.ai/code).

If you don't use Claude Code, you can safely ignore this directory — it has no effect on the application.

---

## What's Here

### `agents/`

Specialized sub-agents that Claude Code can spin up for focused tasks:

| Agent | Purpose |
|-------|---------|
| `backend-dev` | FastAPI, Python, DuckDB — backend features and fixes |
| `frontend-dev` | React 19, TypeScript, Milkdown — UI components and state |
| `code-reviewer` | PR review, conventions, security, performance |
| `db-analyst` | DuckDB/Postgres schema, queries, migrations |
| `debugger` | Errors, test failures, unexpected behavior |
| `doc-writer` | README, ai_docs, changelogs, docstrings |
| `infra-security` | Docker, env vars, security review, cloud setup |
| `librarian` | Navigates `ai_docs/` to answer architecture questions |
| `test-runner` | pytest, vitest, coverage, CI |

### `skills/`

Reusable knowledge modules that agents and the main assistant can load:

| Skill | Covers |
|-------|--------|
| `ai-docs` | How to navigate and update `ai_docs/` |
| `api-conventions` | FastAPI endpoint patterns for this project |
| `backup` | Backup/restore workflows |
| `brand-guidelines` | Colors, typography, tone |
| `clear-tasks` | Kanban task management |
| `code-review` | Review checklist and output format |
| `daily-note` | Daily note structure and templates |
| `dev-workflow` | Branching, commits, PRs |
| `duckdb-query` | DuckDB schemas and query patterns |
| `editor-ux` | Milkdown editor UX patterns |
| `excalidraw` | Diagram generation reference |
| `extract-data` | AI extraction pipeline |
| `frontend-patterns` | React hooks, API calls, component patterns |
| `infra-review` | Security and infrastructure checklist |
| `performance-optimization` | Query and render performance |
| `python-conventions` | Ruff, type hints, async patterns |
| `setup-cloud` | Postgres + cloud deployment |
| `task-integration` | Task ↔ daily note sync |
| `update-docs` | When and how to update documentation |

---

## Usage

When you open this project in Claude Code, the agents and skills are auto-discovered. You can:

- Ask Claude to use a specific agent: *"Use the backend-dev agent to add a new API endpoint"*
- Reference skills directly: *"Follow the dev-workflow skill to create a branch"*
- Let Claude pick automatically — it will load relevant skills based on context

---

## Local Settings

If you want to customise Claude Code's permissions or preferences for this project on your machine, create:

```
.claude/settings.local.json
```

This file is **gitignored** — your local settings won't affect other contributors.

See the [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) for the settings schema.
