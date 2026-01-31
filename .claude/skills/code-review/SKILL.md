---
name: code-review
description: Review code for quality, security, and best practices. Use after writing or modifying code, before commits.
context: fork
agent: code-reviewer
allowed-tools: Read, Grep, Glob, Bash(git *)
---

# Code Review

Perform a comprehensive code review of the current changes.

## Review Process

1. **Get the changes**: Run `git diff` to see unstaged changes, `git diff --staged` for staged changes
2. **Identify modified files**: Focus review on changed files
3. **Review systematically**: Check each file against the criteria below

## Review Criteria

### Code Quality
- Clear, readable code with meaningful names
- No code duplication (DRY principle)
- Functions are focused and small
- Proper error handling

### Security (CRITICAL)
- No hardcoded secrets, API keys, or credentials
- Input validation on external data
- SQL injection prevention (parameterized queries)
- XSS prevention in frontend code

### Best Practices by Tech
**Python/FastAPI:**
- Type hints on function signatures
- Pydantic models for request/response
- Async/await used appropriately
- Dependencies injected properly

**React/TypeScript:**
- Components are focused and reusable
- Hooks follow rules of hooks
- Proper TypeScript types (no `any`)
- Effects have proper cleanup

**DuckDB:**
- Queries are parameterized
- Appropriate use of CTEs
- Indexes considered for performance

## Output Format

Organize findings by severity:

### Critical (Must Fix)
Issues that block merge: security vulnerabilities, broken functionality

### Warnings (Should Fix)
Issues that should be addressed: code smells, potential bugs

### Suggestions (Consider)
Improvements for maintainability or performance

For each issue, provide:
- File and line number
- Current code snippet
- Explanation of the issue
- Suggested fix
