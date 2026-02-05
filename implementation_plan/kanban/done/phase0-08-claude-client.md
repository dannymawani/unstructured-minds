# Claude Client

**Phase:** 0 - Foundation
**Priority:** Critical
**Completed:** 2026-01-31

## Description

Implement the Claude API client for data extraction and natural language queries.

## Tasks

- [x] Create ClaudeClient class with Anthropic SDK
- [x] Add extraction method (Haiku for speed)
- [x] Add query method (Sonnet for complex queries)
- [x] Implement retry logic with exponential backoff
- [x] Handle rate limiting gracefully

## Acceptance Criteria

- Client initializes with API key
- Extraction returns valid JSON
- Query returns natural language response
- Retries on transient failures

## Key Files

- `backend/src/claude/client.py`
- `backend/src/claude/prompts.py`

## Models Used

- `claude-haiku-4-5-20251001` - Fast extraction
- `claude-sonnet-4-20250514` - Complex queries
