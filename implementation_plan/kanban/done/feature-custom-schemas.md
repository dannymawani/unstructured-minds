# Custom Extraction Schemas

**Phase:** 5 - Extensibility
**Priority:** Medium
**Status:** Not Started

## Description

Allow users to define custom data extraction schemas for their specific use cases.

## Tasks

- [ ] Schema editor UI
- [ ] Schema validation
- [ ] Custom schema storage
- [ ] Schema versioning
- [ ] Example-driven schema creation
- [ ] Schema testing interface

## Acceptance Criteria

- Users can create custom schemas
- Schemas validated before save
- Extraction uses custom schemas
- Can test schema against sample notes
- Versioning prevents data loss

## Schema Definition

```json
{
  "name": "book_notes",
  "version": "1.0",
  "description": "Extract book reading notes",
  "fields": [
    {"name": "title", "type": "string", "required": true},
    {"name": "author", "type": "string"},
    {"name": "rating", "type": "integer", "min": 1, "max": 5},
    {"name": "quotes", "type": "array", "items": "string"},
    {"name": "finished_date", "type": "date"}
  ],
  "extraction_hints": "Look for book titles in headers or 'Reading:' sections"
}
```

## UI Flow

1. Name and describe schema
2. Add fields with types
3. Provide extraction hints
4. Test against sample note
5. Save and activate
