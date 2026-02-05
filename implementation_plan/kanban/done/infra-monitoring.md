# Monitoring & Observability

**Phase:** 5 - Extensibility
**Priority:** Medium
**Status:** Not Started

## Description

Add monitoring, logging, and observability for production reliability.

## Tasks

- [ ] Structured logging (JSON)
- [ ] Error tracking (Sentry)
- [ ] Health check endpoints
- [ ] Metrics collection
- [ ] Log aggregation
- [ ] Alerting setup

## Acceptance Criteria

- All errors logged with context
- Health checks for all components
- Key metrics tracked
- Alerts on critical failures
- Logs searchable

## Health Endpoints

```
GET /health           -> Basic health
GET /health/ready     -> Ready to serve
GET /health/live      -> Liveness probe
GET /health/detailed  -> Component status
```

## Metrics to Track

- Request latency (p50, p95, p99)
- Error rate
- Extraction duration
- DuckDB query time
- Active connections
- Memory usage

## Logging Format

```json
{
  "timestamp": "2026-02-05T14:30:00Z",
  "level": "INFO",
  "message": "Extraction completed",
  "context": {
    "file": "Daily-Notes/2026-02-05.md",
    "duration_ms": 450,
    "records_extracted": 5
  }
}
```
