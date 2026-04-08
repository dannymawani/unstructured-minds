---
name: ai-docs
description: Navigate and maintain the ai_docs/ wiki. Use when you need to find, read, or update project documentation.
user-invocable: false
---

# AI Docs Wiki Navigation

## When to Read Which Doc

| If you need to... | Read |
|-------------------|------|
| Understand the big picture | `ai_docs/01-architecture-overview.md` |
| Know what technologies are used and why | `ai_docs/02-technology-stack.md` |
| Start feature work, make commits, or follow process | `ai_docs/03-development-workflow.md` |
| Write queries, change schemas, or understand data | `ai_docs/04-database-architecture.md` |
| Implement or review backend code | `ai_docs/05-backend.md` |
| Implement or review frontend code | `ai_docs/06-frontend.md` |
| Modify extraction, save triggers, or exercise matching | `ai_docs/07-data-pipeline.md` |
| Touch auth, security headers, or write tests | `ai_docs/08-auth-and-security.md` |
| Change Docker config, deploy, or set up environments | `ai_docs/09-infrastructure.md` |
| Check past architectural decisions | `ai_docs/10-decisions-log.md` |

## Routing Rules

1. **Start with the index** — `ai_docs/00-index.md` maps queries to docs
2. **Read only what's relevant** — each doc is self-contained
3. **Follow cross-references** — docs link to each other where topics overlap
4. **Check decisions log first** — before proposing architectural changes

## Updating Docs

After structural changes to the codebase, update the relevant `ai_docs/` file:

1. Identify which doc(s) are affected by the change
2. Edit the relevant section directly — match existing style (tables, concise descriptions)
3. If a significant architectural decision was made, append to `ai_docs/10-decisions-log.md`

**Structural changes:** new/removed endpoints, components, tables, env vars, Docker config, auth changes, dependency changes, storage format changes.

**Skip updates for:** bug fixes, CSS tweaks, copy changes, test additions, refactors that don't change interfaces.

## Decisions Log Format

Append to `ai_docs/10-decisions-log.md`:

```markdown
### YYYY-MM-DD: Decision Title

**Context:** Why this decision was needed
**Decision:** What was decided
**Alternatives:** What else was considered
**Outcome:** Impact on the codebase
```
