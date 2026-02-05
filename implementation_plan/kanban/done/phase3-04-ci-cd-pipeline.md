# CI/CD Pipeline

**Phase:** 3 - Deployment
**Priority:** High
**Status:** Done

## Description

Set up GitHub Actions for continuous integration with testing, linting, and build verification.

## Tasks

- [ ] Backend test job (pytest + coverage)
- [ ] Frontend test job (vitest)
- [ ] Lint job (ruff + eslint)
- [ ] Type check job (mypy + tsc)
- [ ] Docker build verification
- [ ] PR status checks
- [ ] Dependabot configuration

## Acceptance Criteria

- All tests run on PR
- Linting catches issues before merge
- Type errors block merge
- Docker images build successfully
- Coverage reports generated

## .github/workflows/ci.yml

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy src/
      - run: pytest --cov --cov-report=xml

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
      - run: npm run build
```
