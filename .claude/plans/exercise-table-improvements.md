# Exercise Table Improvements Plan

## Phase 1: Historical Data Cleanup
- [x] Script to normalize exercise names in DB (both DuckDB and Postgres)
- [x] Run against Postgres to clean duplicates like Deadlift/deadlift/Deadlifts

## Phase 2: Backend API
- [x] 2.1 Expand ExerciseTableEntry model (total_sets, last_session_sets, is_pr, muscle_groups, trend)
- [x] 2.2 Rewrite SQL: add total_sets, prior_max for PR detection
- [x] 2.3 Update merging logic for new fields
- [x] 2.4 PR detection: only when beat a previous session, not first session
- [x] 2.5 Trend calculation from 3 most recent sessions (up/down/flat/insufficient)
- [x] 2.6 Muscle groups lookup from exercise_definitions.json
- [x] 2.7 Second query for last_session_sets (individual sets from most recent date)
- [x] 2.8 Add muscle_group filter query param

## Phase 3: Frontend
- [x] 3.1 Update TypeScript interfaces
- [x] 3.2 Relative date ("3 days ago" instead of "Mar 8, 2026")
- [x] 3.3 Fix PR badge to use backend is_pr
- [x] 3.4 Trend arrow (up/down/flat icons)
- [x] 3.5 Show total sets column
- [x] 3.6 Muscle group tags below exercise name
- [x] 3.7 Muscle group filter chips above table
- [x] 3.8 Expandable row showing last session sets
- [ ] 3.9 Optional: group by muscle group toggle

## Dependencies
- Phase 1: standalone
- Phase 2: independent of Phase 1
- Phase 3: depends on Phase 2

## Key Files
- backend/src/api/dashboard.py (endpoint, models, SQL)
- frontend/src/components/Dashboard/ExerciseTable.tsx
- shared/exercise_definitions.json (muscle groups)
- backend/src/extraction/exercise_matcher.py
