# Webhooks & Integrations

**Phase:** 5 - Extensibility
**Priority:** Low
**Status:** Not Started

## Description

Support webhooks and integrations with external services for automation.

## Tasks

- [ ] Webhook configuration
- [ ] Event types (note created, extraction complete)
- [ ] Webhook testing
- [ ] Retry logic
- [ ] Integration templates (Zapier, n8n)
- [ ] API keys for external access

## Acceptance Criteria

- Can configure webhook URLs
- Events trigger POST requests
- Failed webhooks retry
- Can test webhooks manually
- Secure with signing

## Webhook Events

- `note.created`
- `note.updated`
- `note.deleted`
- `extraction.completed`
- `daily.created`

## Webhook Payload

```json
{
  "event": "extraction.completed",
  "timestamp": "2026-02-05T14:30:00Z",
  "data": {
    "file_path": "Daily-Notes/2026-02/2026-02-05.md",
    "extracted": {
      "exercise_log": 3,
      "daily_metrics": 1
    }
  },
  "signature": "sha256=..."
}
```

## Integration Ideas

- Send daily summary to Slack
- Add tasks to Todoist
- Log workouts to fitness app
- Sync with calendar
