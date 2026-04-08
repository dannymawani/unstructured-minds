---
name: test
description: Run tests for the project (Python pytest, JavaScript/TypeScript tests)
disable-model-invocation: true
allowed-tools: Bash(pytest *), Bash(npm *), Bash(npx *)
---

# Test Runner

Run tests for the Unstructured Minds project.

## Test Commands

### Backend (Python/FastAPI)
```bash
# Run all backend tests
cd backend && pytest

# Run with coverage
cd backend && pytest --cov=src --cov-report=term-missing

# Run specific test file
cd backend && pytest tests/test_$ARGUMENTS.py -v

# Run tests matching pattern
cd backend && pytest -k "$ARGUMENTS" -v
```

### Frontend (React/TypeScript)
```bash
# Run all frontend tests
cd frontend && npm test

# Run with coverage
cd frontend && npm test -- --coverage

# Run specific test
cd frontend && npm test -- $ARGUMENTS
```

## Execution

1. Determine which tests to run based on $ARGUMENTS:
   - No args: run all tests for both frontend and backend
   - `backend` or `python`: run Python tests only
   - `frontend` or `js` or `react`: run frontend tests only
   - Specific pattern: run matching tests

2. Execute the appropriate test command

3. Report results:
   - Total tests run
   - Passed/Failed counts
   - Coverage summary if available
   - Failed test details with error messages

## Arguments

$ARGUMENTS
