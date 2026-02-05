# Daily Note Skill

**Phase:** 1 - Core MVP
**Priority:** High
**Completed:** 2026-02-02

## Description

Implement the /daily skill that creates daily notes from templates with task rollover.

## Tasks

- [x] POST /skills/daily endpoint
- [x] Template generation with date headers
- [x] Task rollover from previous day
- [x] Daily Note button in UI
- [x] Handle existing note (return existing)

## Acceptance Criteria

- /daily creates note at Daily-Notes/YYYY-MM/YYYY-MM-DD.md
- Template includes standard sections
- Incomplete tasks from yesterday copied
- Button triggers skill with one click

## Key Files

- `backend/src/skills/daily.py`
- `backend/src/api/skills.py`

## Template Sections

- Date header
- Morning metrics (sleep, mood)
- Tasks (with rollover)
- Notes
- Evening reflection
