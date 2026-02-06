# Docker Validation & Test Baseline

**Phase:** 6 - Before Starting
**Priority:** Critical
**Status:** Done
**Completed:** 2026-02-06

## Description

Spin up the full app with `docker compose -f docker-compose.dev.yml up`, verify all services start, run backend + frontend tests to establish a baseline. Document any failures.

## Tasks

- [x] Run `docker compose -f docker-compose.dev.yml up -d`
- [x] Verify backend starts and health endpoint responds
- [x] Verify frontend builds and loads in browser
- [x] Run `cd backend && pytest` — record pass/fail
- [x] Run `cd frontend && npm test` — record pass/fail
- [x] Document baseline test results
- [ ] Fix any blocking startup issues

## Acceptance Criteria

- All Docker services start without errors
- Health endpoint returns 200
- Frontend loads in browser
- Test baseline documented (even if some tests fail)

## Baseline Test Results (2026-02-06)

### Docker Services
- **Docker version:** 28.5.2
- **Backend:** UP (healthy) on port 8000
- **Frontend:** UP on port 5173
- **Health endpoint:** `{"status":"healthy"}` — 200 OK

### Backend Tests
- **Cannot run locally** — missing deps (structlog, anthropic not in local Python)
- **Cannot run in Docker** — pytest not installed in prod image
- **Action needed:** Add test dependencies to Dockerfile or create a test Dockerfile
- **12 test files failed to collect** due to missing imports

### Frontend Tests
- **Total:** 58 tests across 6 files
- **Passed:** 33
- **Failed:** 12
- **Errors:** 1 (OOM crash on Dashboard.test.tsx)

**Failing test files:**
| File | Passed | Failed | Notes |
|------|--------|--------|-------|
| Chat.test.tsx | 4 | 9 | UI interaction tests (submit, enter, loading, error) |
| FileTree.test.tsx | 12 | 3 | API rendering + interaction (timeout/waitFor issues) |
| Dashboard.test.tsx | — | — | OOM crash (JavaScript heap out of memory) |

**Passing test files:**
| File | Passed |
|------|--------|
| button.test.tsx | 5 |
| InsightsCard.test.tsx | 7 |
| MarkdownEditor.test.tsx | 5 |
