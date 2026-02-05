# Template System

**Phase:** 4 - Advanced Features
**Priority:** Medium
**Status:** Not Started

## Description

Allow users to create and use custom templates for different note types.

## Tasks

- [ ] Template storage in vault/Templates/
- [ ] Template variables ({{date}}, {{title}})
- [ ] Template selection UI
- [ ] Quick template insertion
- [ ] Default templates (daily, meeting, project)
- [ ] Template editing

## Acceptance Criteria

- Templates stored as markdown
- Variables substituted on creation
- Can select template when creating note
- Built-in templates for common use cases
- Custom templates supported

## Template Variables

```markdown
{{date}}        -> 2026-02-05
{{date:YYYY}}   -> 2026
{{time}}        -> 14:30
{{title}}       -> Note title
{{cursor}}      -> Cursor position after creation
```

## Default Templates

1. **Daily Note** - Standard daily structure
2. **Meeting Notes** - Attendees, agenda, action items
3. **Project** - Goals, tasks, timeline
4. **Weekly Review** - Reflection prompts

## API

```
GET  /templates          -> List templates
GET  /templates/{name}   -> Get template content
POST /templates          -> Create template
POST /notes/from-template -> Create note from template
```
