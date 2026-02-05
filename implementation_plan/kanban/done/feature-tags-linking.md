# Tags and Bidirectional Linking

**Phase:** 4 - Advanced Features
**Priority:** Medium
**Status:** Not Started

## Description

Support #tags and [[wiki-links]] for organizing and connecting notes.

## Tasks

- [ ] Parse #tags from markdown
- [ ] Parse [[wiki-links]]
- [ ] Tag index in DuckDB
- [ ] Backlinks panel
- [ ] Tag cloud/browser
- [ ] Click tag to search
- [ ] Auto-complete for links

## Acceptance Criteria

- #tags extracted during parsing
- [[links]] create connections
- Backlinks show all references
- Tag browser shows all tags with counts
- Auto-complete suggests existing notes

## Data Model

```sql
CREATE TABLE tags (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE,
    count INTEGER DEFAULT 0
);

CREATE TABLE note_tags (
    note_path TEXT,
    tag_id TEXT,
    PRIMARY KEY (note_path, tag_id)
);

CREATE TABLE links (
    source_path TEXT,
    target_path TEXT,
    link_text TEXT,
    PRIMARY KEY (source_path, target_path)
);
```

## UI Components

- Tag pills in editor
- Backlinks panel (sidebar)
- Tag browser page
- Link preview on hover
