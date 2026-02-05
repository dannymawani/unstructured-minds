# Calendar View

**Phase:** 4 - Advanced Features
**Priority:** Medium
**Status:** Not Started

## Description

Add a calendar view for navigating notes by date and visualizing activity.

## Tasks

- [ ] Monthly calendar component
- [ ] Day cells with activity indicators
- [ ] Click to open/create daily note
- [ ] Heatmap overlay (activity intensity)
- [ ] Week/month/year views
- [ ] Navigate between months

## Acceptance Criteria

- Calendar displays current month
- Days with notes are highlighted
- Click day opens that day's note
- Empty day click creates note
- Activity heatmap shows intensity

## UI Design

```
     February 2026
Su Mo Tu We Th Fr Sa
                   1
 2  3  4  5  6  7  8
 9 10 11 12 13 14 15
16 17 18 19 20 21 22
23 24 25 26 27 28

[Filled dots indicate days with notes]
[Color intensity shows activity level]
```

## API

```
GET /calendar/month?year=2026&month=2
{
  "days": [
    {"date": "2026-02-01", "has_note": true, "activity_level": 3},
    {"date": "2026-02-02", "has_note": false, "activity_level": 0},
    ...
  ]
}
```

## Key Files

- `frontend/src/components/Calendar/`
- `backend/src/api/calendar.py`
