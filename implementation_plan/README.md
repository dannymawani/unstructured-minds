# Implementation Plan

> Detailed planning documents for building Unstructured Minds.

See the [main README](../README.md) for project overview.

## Core Principles (Non-Negotiable)

1. **Markdown files as source of truth** - Human-readable, portable, version-controllable
2. **Claude is optional** - Core app works without it, Claude adds enhanced features
3. **Local-first with pluggable storage** - Local filesystem first, optional cloud backends (Azure Blob, S3, GCP)
4. **DuckDB as query engine** - Fast analytics over structured data
5. **No Obsidian dependency** - Standalone web application (Docker)
6. **Single workspace** - No vault concept, one workspace per installation

## Chosen Stack (January 2026)

| Layer | Technology | Version |
|-------|------------|---------|
| Deployment | Docker Compose | - |
| Frontend | React + Milkdown | 19 / 7.x |
| Backend | Python + FastAPI | 3.12 / 0.115.x |
| Database | DuckDB | 1.4 |
| AI | Claude API (optional) | Haiku / Sonnet |

## Planning Documents

| Document | Purpose | Status |
|----------|---------|--------|
| [01-VISION.md](./01-VISION.md) | Product vision, user stories, scope | Draft |
| [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) | System architecture options | Draft |
| [03-FRONTEND.md](./03-FRONTEND.md) | Frontend framework comparison | Draft |
| [04-DATA-LAYER.md](./04-DATA-LAYER.md) | DuckDB, storage, schema design | Draft |
| [05-LLM-INTEGRATION.md](./05-LLM-INTEGRATION.md) | Claude API integration patterns | Draft |
| [06-IMPLEMENTATION.md](./06-IMPLEMENTATION.md) | Phased implementation roadmap | Draft |
| [07-DECISIONS.md](./07-DECISIONS.md) | Decision log with rationale | Draft |
| [08-ARCHITECTURE-DIAGRAMS.md](./08-ARCHITECTURE-DIAGRAMS.md) | Visual diagrams, flowcharts, versions | Complete |
| [09-IMPLEMENTATION-PLAN-AND-STEPS.md](./09-IMPLEMENTATION-PLAN-AND-STEPS.md) | Step-by-step build plan, tests, branches | **New** |

## Git Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Main development branch (protected) |
| `feature/<name>` | Feature branches |
| `release/<version>` | Release branches |

All development happens in feature branches. PRs required to merge to `main`.

See [09-IMPLEMENTATION-PLAN-AND-STEPS.md](./09-IMPLEMENTATION-PLAN-AND-STEPS.md) for full workflow.

## Quick Navigation

- **Starting point?** → Read [01-VISION.md](./01-VISION.md)
- **Technical deep-dive?** → Read [02-ARCHITECTURE.md](./02-ARCHITECTURE.md)
- **What framework?** → Read [03-FRONTEND.md](./03-FRONTEND.md)
- **Ready to build?** → Read [09-IMPLEMENTATION-PLAN-AND-STEPS.md](./09-IMPLEMENTATION-PLAN-AND-STEPS.md)

## Current Status

🟡 **Planning Phase** - Exploring options before implementation

---

*Created: 2026-01-31*
