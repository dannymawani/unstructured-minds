---
name: pr-summary
description: Summarize a pull request for review
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

# PR Summary

Summarize a pull request for review.

## Pull Request Context

- PR diff: !`gh pr diff $ARGUMENTS 2>/dev/null || echo "No PR specified or not found"`
- PR details: !`gh pr view $ARGUMENTS --json title,body,author,labels,reviewRequests 2>/dev/null || echo ""`
- Changed files: !`gh pr diff $ARGUMENTS --name-only 2>/dev/null || echo ""`

## Analysis Tasks

1. **Summarize changes**: What does this PR do in 2-3 sentences?

2. **List key changes by file**:
   - What files were modified?
   - What is the main change in each?

3. **Identify potential issues**:
   - Security concerns
   - Breaking changes
   - Missing tests
   - Performance implications

4. **Review checklist**:
   - [ ] Code follows project conventions
   - [ ] Tests added/updated
   - [ ] Documentation updated if needed
   - [ ] No secrets or sensitive data

## Arguments

PR number: $ARGUMENTS
