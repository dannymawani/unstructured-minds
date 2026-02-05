# Full-Text Search

**Phase:** 4 - Advanced Features
**Priority:** High
**Status:** Done

## Description

Implement full-text search across all vault notes with instant results and search highlighting.

## Tasks

- [ ] Search index using DuckDB FTS
- [ ] POST /search endpoint
- [ ] Search UI component
- [ ] Real-time search results
- [ ] Search result highlighting
- [ ] Search within current folder
- [ ] Recent searches history

## Acceptance Criteria

- Search returns results in <100ms
- Results show context snippets
- Query terms highlighted
- Can scope to folder
- Fuzzy matching supported

## API

```
POST /search
{
  "query": "exercise squat",
  "folder": "Daily-Notes",  // optional
  "limit": 20
}

Response:
{
  "results": [
    {
      "path": "Daily-Notes/2026-02/2026-02-01.md",
      "title": "2026-02-01",
      "snippet": "Did 5x5 **squat** at 225lbs...",
      "score": 0.95
    }
  ]
}
```

## Key Files

- `backend/src/search/index.py`
- `frontend/src/components/Search/`
