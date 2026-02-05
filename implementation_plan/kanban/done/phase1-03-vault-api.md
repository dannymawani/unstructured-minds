# Vault API Endpoints

**Phase:** 1 - Core MVP
**Priority:** Critical
**Completed:** 2026-02-01

## Description

Create REST API endpoints for managing markdown files in the vault.

## Tasks

- [x] GET /vault/files - List all files as tree
- [x] GET /vault/file - Read file content
- [x] POST /vault/file - Create/update file
- [x] DELETE /vault/file - Delete file
- [x] Handle nested folder structures

## Acceptance Criteria

- File tree returns proper hierarchy
- Read returns file content and metadata
- Write creates parent directories if needed
- Delete removes file from storage

## Key Files

- `backend/src/api/routes.py`
- `backend/src/api/vault.py`

## API Endpoints

```
GET  /vault/files              -> FileTree
GET  /vault/file?path=...      -> FileContent
POST /vault/file               -> {path, content}
DELETE /vault/file?path=...    -> Success
```
