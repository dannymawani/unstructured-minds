# Quick Capture

**Phase:** 4 - Advanced Features
**Priority:** Medium
**Status:** Not Started

## Description

Add quick capture functionality for rapidly adding notes without full app navigation.

## Tasks

- [ ] Quick capture modal (Cmd+Shift+N)
- [ ] Auto-append to daily note
- [ ] Capture with timestamp
- [ ] Voice-to-text option
- [ ] Quick capture widget
- [ ] Browser extension concept

## Acceptance Criteria

- Modal opens instantly
- Text captured to daily note
- Timestamps automatically added
- Works from any screen
- Minimal friction

## Quick Capture Flow

1. Press Cmd+Shift+N (or click widget)
2. Type quick note
3. Press Enter to save
4. Note appended to today's daily note

## Capture Format

```markdown
## Quick Notes

- 14:30 - Remember to call mom
- 15:45 - Great idea for the project!
- 16:20 - Book recommendation: "Thinking Fast and Slow"
```

## API

```
POST /capture
{
  "text": "Remember to buy groceries",
  "target": "daily"  // or specific file path
}
```

## Implementation Options

- Global keyboard shortcut (desktop)
- PWA notification action
- Share target (mobile)
