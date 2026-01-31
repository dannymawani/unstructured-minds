---
name: commit
description: Create a well-structured git commit with a descriptive message
disable-model-invocation: true
allowed-tools: Bash(git *)
---

# Smart Commit

Create a git commit with a well-structured message following conventional commit format.

## Process

1. Run `git status` to see all changes
2. Run `git diff --staged` to see staged changes (if any)
3. Run `git diff` to see unstaged changes
4. Analyze the changes to understand what was done

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `chore`: Build, config, or tooling changes
- `style`: Code style/formatting changes

### Guidelines
- Subject line: imperative mood, lowercase, no period, max 50 chars
- Body: explain WHY not WHAT (the diff shows what)
- Reference issue numbers if applicable: `Fixes #123`

## Execution

1. If no files are staged, suggest which files to stage based on logical grouping
2. Create the commit with the formatted message
3. Show the resulting commit hash and summary

## Arguments

$ARGUMENTS

If arguments are provided, use them as guidance for the commit scope or message.
