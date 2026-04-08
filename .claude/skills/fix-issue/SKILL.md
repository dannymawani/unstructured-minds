---
name: fix-issue
description: Fix a GitHub issue by number
disable-model-invocation: true
allowed-tools: Bash(gh *), Read, Edit, Write, Grep, Glob
---

# Fix GitHub Issue

Implement a fix for a GitHub issue.

## Process

1. **Fetch the issue**
   ```bash
   gh issue view $ARGUMENTS --json title,body,labels,comments
   ```

2. **Understand requirements**
   - Read the issue description
   - Check comments for clarifications
   - Identify acceptance criteria

3. **Find relevant code**
   - Search for related files
   - Understand the current implementation
   - Identify where changes are needed

4. **Implement the fix**
   - Make minimal, focused changes
   - Follow project conventions (see api-conventions, python-conventions, frontend-patterns skills)
   - Add/update tests if applicable

5. **Verify**
   - Run relevant tests
   - Manual verification if needed

6. **Prepare commit**
   - Stage only relevant files
   - Create commit message referencing issue: `fix: description (fixes #$ARGUMENTS)`

## Guidelines

- Keep changes focused on the issue
- Don't refactor unrelated code
- If the issue is unclear, list questions before implementing
- If the fix is complex, explain your approach first

## Arguments

Issue number: $ARGUMENTS
