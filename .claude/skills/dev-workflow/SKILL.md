---
name: dev-workflow
description: Mandatory development workflow for Unstructured Minds. Covers the plan-approve-implement-test-review-deploy process, branching strategy, and pre-work checklist. Reference before starting any feature work.
user-invocable: false
---

# Development Workflow

## Mandatory Process

Every feature or change follows this sequence. No exceptions.

```
Plan → Approve → Implement → Test → Review → Deploy
```

### 1. Plan
- Create a kanban task in `implementation_plan/kanban/not_started/`
- Write a clear description with acceptance criteria
- Identify affected files and components
- Consider data migration needs
- Use Claude's plan mode for non-trivial features

### 2. Approve
- Review the plan with the user before writing code
- Confirm approach, scope, and acceptance criteria
- Move kanban task to `in_progress/`

### 3. Implement
- Create a feature branch: `feature/{name}` (e.g., `feature/data-integration`)
- Write code in small, focused commits
- Follow existing patterns (see api-conventions, python-conventions, frontend-patterns skills)
- No direct commits to `main`

### 4. Test
- Run all tests before committing: `/test`
- Backend: `pytest` in `backend/tests/`
- Frontend: `vitest` in `frontend/`
- Add tests for new functionality
- Verify Docker build: `docker compose -f docker-compose.dev.yml build`

### 5. Review
- Run `/code-review` before merging
- Check for security issues, code quality, conventions
- Verify acceptance criteria are met

### 6. Deploy
- Merge feature branch to `main`
- Move kanban task to `done/`
- Verify Docker Compose still works end-to-end
- Update documentation if needed

## Branching Strategy

```
main (protected)
├── feature/data-integration
├── feature/extraction-performance
├── feature/editor-ux
├── feature/task-integration
└── feature/dev-workflow
```

### Rules
- **Never commit directly to `main`** — always use feature branches
- Branch names: `feature/{descriptive-name}` for features, `fix/{issue}` for bugfixes
- One feature per branch (can have multiple related tasks)
- Rebase on main before merging (keep history clean)
- Delete branch after merge

## Pre-Work Checklist

Before starting any implementation task, verify:

- [ ] Docker is running: `docker compose -f docker-compose.dev.yml up -d`
- [ ] Backend tests pass: `cd backend && pytest`
- [ ] Frontend tests pass: `cd frontend && npm test`
- [ ] Feature branch created: `git checkout -b feature/{name}`
- [ ] Kanban task exists in `not_started/` or `in_progress/`
- [ ] Plan has been reviewed and approved

## Commit Conventions

Use the `/commit` skill for well-structured commits. General rules:

- Imperative mood: "Add feature" not "Added feature"
- Short subject line (< 72 chars)
- Body explains "why" not "what"
- Reference kanban task in commit body when relevant

## Quick Reference

| Action | Command |
|--------|---------|
| Start work | `git checkout -b feature/{name}` |
| Run tests | `/test` |
| Review code | `/code-review` |
| Commit | `/commit` |
| Create PR | `gh pr create` |

## Feature Branches for Upcoming Work

| Branch | Tasks |
|--------|-------|
| `feature/data-integration` | Data migration, template merge, daily notes import, config integration |
| `feature/extraction-performance` | Three-tier save model, extraction timing fix |
| `feature/editor-ux` | Template UX, WYSIWYG toolbar, autosave |
| `feature/task-integration` | Task API, personal kanban UI |
| `feature/dev-workflow` | Documentation, workflow setup |
