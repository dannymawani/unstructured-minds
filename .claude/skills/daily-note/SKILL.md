---
name: daily-note
description: Create a new daily note with template
disable-model-invocation: true
allowed-tools: Write, Read, Bash(date *)
---

# Create Daily Note

Create a new daily note from template.

## Template

```markdown
# $DATE

## Morning Checklist
- [ ] Review yesterday's tasks
- [ ] Set today's priorities
- [ ] Check calendar

## Tasks
- [ ]

## Training


## Food
- Breakfast:
- Lunch:
- Dinner:

## Notes


## End of Day
- Energy: /10
- Mood: /10
- What went well:
- What could improve:
```

## Process

1. Get today's date (or use provided date)
2. Determine file path: `vault/Daily-Notes/YYYY-MM/YYYY-MM-DD.md`
3. Check if note already exists
4. If not, create from template
5. Check for incomplete tasks from previous day to roll over

## Task Rollover

Search previous day's note for tasks marked with `- [ ]` (incomplete).
Offer to add them to today's note with `-> moved from YYYY-MM-DD` annotation.

## Arguments

$ARGUMENTS

- No args: Create note for today
- Date string: Create note for specified date (e.g., "2026-01-15")
