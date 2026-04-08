---
name: update-docs
description: Analyze recent code changes and update relevant documentation. Detects what changed and updates affected docs, README, and changelogs.
user-invocable: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git diff *), Bash(git log *)
---

# Update Documentation

Analyze code changes and update relevant documentation files.

## Process

1. **Detect what changed** -- Read git diff (staged + unstaged) to identify modified files
2. **Categorize changes** -- Classify by type: code, API, feature, architecture, config, dependency
3. **Update affected docs** -- Modify the relevant documentation files
4. **Report results** -- Show what was updated and what needs manual review

## Step 1: Detect Changes

Run `git diff --stat HEAD` and `git diff --staged --stat` to see what files changed.

If the user passes `$ARGUMENTS`, use that to scope the diff (e.g., a commit range or `--staged`).

Categorize each changed file:

| Path Pattern | Category |
|-------------|----------|
| `backend/src/api/` | API change |
| `backend/src/claude/` | AI integration |
| `backend/src/db/` | Database/schema |
| `frontend/src/components/` | Frontend feature |
| `frontend/src/hooks/` | Frontend architecture |
| `frontend/src/lib/` | Frontend utilities |
| `frontend/package.json` | Dependency change |
| `backend/pyproject.toml` | Dependency change |
| `docker-compose*.yml` | Infrastructure |
| `.claude/skills/` | Skills/workflow |
| `docs/` | Documentation (skip -- already docs) |

## Step 2: Update Affected Docs

### For dependency changes (package.json, pyproject.toml)

- Read `docs/tech-stack.md`
- Check if the added/removed dependency is listed
- Update version numbers or add/remove entries as needed

### For API changes (backend/src/api/)

- Read `CLAUDE.md` skills/agents tables
- Check if new endpoints need to be documented
- Update the SQL_GENERATION_PROMPT table schema in query.py docs if schema changed

### For new features (new component directories or significant new files)

- Read `docs/sales.md` feature showcase section
- Read `README.md` features table
- Add the new feature if not already listed

### For architecture changes (hooks, lib, db, infrastructure)

- Read `docs/tech-stack.md` architecture sections
- Flag that excalidraw diagrams in `docs/architecture/` may need updating
- Update data flow descriptions if the pipeline changed

### For configuration changes (config.py, .env.example, docker-compose)

- Read `docs/.env.example`
- Ensure new environment variables are documented with comments
- Update `docs/SECURITY.md` deployment checklist if security-relevant

## Step 3: Report

Output a summary in this format:

```
## Documentation Update Report

### Updated Files
- `docs/tech-stack.md` -- Added new dependency X
- `README.md` -- Updated feature table

### Needs Manual Review
- `docs/architecture/system-architecture.excalidraw` -- Architecture changed, diagram may be outdated
- `CLAUDE.md` -- New API endpoint added, verify skills table

### Version Bump Suggestion
Recommend running `/changelog` with:
- Patch (bug fix / minor docs)
- Minor (new feature / API addition)
- Major (breaking change / architecture refactor)
```

## Arguments

$ARGUMENTS

Default: analyze uncommitted changes (`git diff HEAD`).

Options:
- A commit range (e.g., `main..HEAD`) to analyze branch changes
- `--staged` to only analyze staged changes
- `--dry-run` to report without modifying files
