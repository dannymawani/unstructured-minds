# Contributing to Unstructured Minds

Thanks for your interest in contributing! Here's how to get started.

## Quick Start

1. Fork the repo and clone your fork
2. Create a branch: `git checkout -b feature/your-feature` or `fix/your-fix`
3. Make your changes
4. Run tests: `make test`
5. Push and open a PR

## Development Setup

```bash
cp .env.example .env
# Edit .env — add LLM_API_KEY if you want AI features

# With Docker (recommended)
make dev

# Without Docker
cd backend && pip install -e ".[dev]" && python3 -m uvicorn src.main:app --reload
cd frontend && npm install && npm run dev
```

## Code Style

**Backend (Python):**
- Format with [Ruff](https://docs.astral.sh/ruff/) — `ruff check . && ruff format .`
- Type hints on public functions
- 100 char line length

**Frontend (TypeScript/React):**
- TypeScript strict mode
- `npm run typecheck` must pass
- Functional components with hooks

## Tests

All PRs must pass existing tests. Add tests for new features.

```bash
make test-backend      # pytest
make test-frontend     # vitest
make typecheck         # tsc --noEmit
```

## Branching

| Branch pattern | Purpose |
|---------------|---------|
| `feature/{name}` | New features |
| `fix/{name}` | Bug fixes |
| `docs/{name}` | Documentation changes |

Never commit directly to `main`.

## Pull Requests

- Keep PRs focused — one feature or fix per PR
- Write a clear description of what changed and why
- Link related issues with "Fixes #123" or "Closes #123"
- Add screenshots for UI changes

## Commit Messages

Write concise commit messages that explain *why*, not just *what*.

```
feat: add Ollama provider support for local LLM inference
fix: prevent duplicate extraction on rapid autosave
docs: update self-hosting guide for Postgres mode
```

## Reporting Issues

Use the [issue templates](https://github.com/dannymawani/unstructured-minds/issues/new/choose) for bug reports and feature requests.

## Questions?

Open a [discussion](https://github.com/dannymawani/unstructured-minds/discussions) or comment on a relevant issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
