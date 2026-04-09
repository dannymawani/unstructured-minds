# Development Workflow

Branching strategy, commit conventions, PR process, testing, and documentation practices.

## Process

Every feature or change follows this sequence:

```
Plan → Approve → Implement → Test → Review → Deploy
```

### 1. Plan
- Create a kanban task for the work
- Write clear description with acceptance criteria
- Identify affected files and components
- Use Claude's plan mode for non-trivial features

### 2. Approve
- Review the plan with the user before writing code
- Confirm approach, scope, and acceptance criteria

### 3. Implement
- Create a feature branch (never commit to `main`)
- Write code in small, focused commits
- Follow existing patterns (see [05-backend](05-backend.md), [06-frontend](06-frontend.md))

### 4. Test
- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test`
- Add tests for new functionality
- Verify Docker build if infrastructure changed

### 5. Review
- Run `/code-review` before merging
- Check for security issues, code quality, conventions

### 6. Deploy
- Merge feature branch to `main`
- Verify Docker Compose works end-to-end
- Update documentation if structural changes were made

## Branching Strategy

```
main (protected)
├── feature/{descriptive-name}    # New features
└── fix/{issue-description}       # Bug fixes
```

**Rules:**
- Never commit directly to `main`
- One feature per branch (can have multiple related tasks)
- Rebase on main before merging
- Delete branch after merge

## Commit Conventions

Format:
```
<type>(<scope>): <subject>

<body — explain WHY not WHAT>

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`

**Rules:**
- Imperative mood: "Add feature" not "Added feature"
- Short subject line (< 72 chars)
- Stage specific files (`git add <files>`), not `git add .`
- Check with `git diff --cached --stat`

## Testing

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test

# Type checking
cd frontend && npm run typecheck
```

See [08-auth-and-security](08-auth-and-security.md) for how tests bypass auth.

## Documentation Updates

After **structural changes**, update the relevant `ai_docs/` file. Structural changes include:

- Adding/removing/renaming API endpoints or routers
- Adding/removing/renaming frontend components, hooks, or views
- Changing database tables, columns, or indexes
- Adding/removing environment variables or config fields
- Changing Docker services, volumes, or build configuration
- Modifying auth flow, middleware, or dependency injection
- Adding/removing dependencies (backend or frontend)
- Changing storage backends or data file formats

**Skip updates for:** Bug fixes, CSS tweaks, copy changes, test additions, or refactors that don't change the public interface.

