# Dashboard API

**Phase:** 2 - Polish
**Priority:** High
**Completed:** 2026-02-02

## Description

Create API endpoints that aggregate and return data for dashboard visualizations.

## Tasks

- [x] GET /dashboard/weekly-activity - Notes created per day
- [x] GET /dashboard/metrics-trends - Time series for metrics
- [x] GET /dashboard/exercise-progress - Workout stats
- [x] GET /dashboard/summary - Overview stats

## Acceptance Criteria

- Weekly activity returns 7 days of data
- Metrics trends return configurable date range
- Exercise progress shows improvement over time
- All endpoints handle empty data gracefully

## Key Files

- `backend/src/api/dashboard.py`

## Response Formats

```json
// weekly-activity
{ "data": [{"date": "2026-02-01", "count": 3}, ...] }

// metrics-trends
{ "data": [{"date": "...", "sleep": 7.5, "mood": 4}, ...] }

// exercise-progress
{ "data": [{"exercise": "squat", "max_weight": 225}, ...] }
```
