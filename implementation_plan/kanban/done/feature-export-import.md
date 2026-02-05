# Export/Import Functionality

**Phase:** 4 - Advanced Features
**Priority:** Medium
**Status:** In Progress

## Description

Allow users to export their data in various formats and import data from other sources.

## Tasks

- [ ] Export vault as ZIP
- [ ] Export data as CSV
- [ ] Export data as JSON
- [ ] Import markdown files
- [ ] Import from Obsidian
- [ ] Import from Notion (markdown export)
- [ ] Backup/restore DuckDB

## Acceptance Criteria

- One-click full backup
- CSV export for spreadsheet use
- Can restore from backup
- Import preserves folder structure
- No data loss during import

## API Endpoints

```
GET  /export/vault      -> ZIP file download
GET  /export/data       -> CSV/JSON download
POST /import/files      -> Upload and import
POST /backup            -> Create backup
POST /restore           -> Restore from backup
```

## Export Formats

- **Vault ZIP**: All markdown files with structure
- **Data CSV**: One CSV per table (exercise_log.csv, etc.)
- **Data JSON**: Complete database dump
- **Backup**: DuckDB file + vault + settings
