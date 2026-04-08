# AI Docs Index

Centralized, Claude-optimized documentation for Unstructured Minds. Each doc is a standalone reference — read only what you need.

## Reading Guide

| Doc | Covers | Read when... |
|-----|--------|--------------|
| [01-architecture-overview](01-architecture-overview.md) | System design, two modes, data flow, component relationships | You need the big picture or how pieces connect |
| [02-technology-stack](02-technology-stack.md) | Every technology, version, why chosen, how they interact | Adding dependencies, evaluating alternatives, or onboarding |
| [03-development-workflow](03-development-workflow.md) | Branching, commits, PRs, testing, review, deploy process | Starting any feature work or making commits |
| [04-database-architecture](04-database-architecture.md) | DuckDB + Postgres schemas, two-mode data layer, analytics cache | Writing queries, changing schemas, debugging data issues |
| [05-backend](05-backend.md) | FastAPI structure, API conventions, Python patterns, Claude integration | Implementing or reviewing backend code |
| [06-frontend](06-frontend.md) | React patterns, components, state management, Milkdown editor | Implementing or reviewing frontend code |
| [07-data-pipeline](07-data-pipeline.md) | Extraction flow, exercise matching, AI classification, save model | Modifying extraction, save triggers, or exercise matching |
| [08-auth-and-security](08-auth-and-security.md) | Clerk auth, JWT flow, CSP, SQL validation, testing auth bypass | Touching auth, security headers, or writing tests |
| [09-infrastructure](09-infrastructure.md) | Docker, CI/CD, env vars, cloud setup, backup/restore, LAN access | Changing Docker config, deploying, or setting up environments |


## How to Use

1. **Start here** — scan the table above to find the right doc
2. **Read one doc** — each is self-contained with cross-references where needed

4. **Update after changes** — when making structural changes, update the relevant doc(s)

## Relationship to Other Documentation

- **CLAUDE.md** — Quick-start essentials and routing table (points here)
- **Skills** (`.claude/skills/`) — Task-specific instructions (how to do things)
- **Agents** (`.claude/agents/`) — Specialized worker definitions
- **docs/** — Human-facing documentation (AUTH.md, SECURITY.md, etc.)
- **ai_docs/** (here) — Claude-optimized consolidated reference (how things work)
