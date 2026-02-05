# Performance Optimization

**Phase:** 5 - Extensibility
**Priority:** Medium
**Status:** Not Started

## Description

Optimize application performance for large vaults and heavy usage.

## Tasks

- [ ] Virtual scrolling for file tree
- [ ] Lazy loading for dashboard
- [ ] DuckDB query optimization
- [ ] Frontend bundle splitting
- [ ] API response caching
- [ ] Editor performance with large files
- [ ] Background extraction queue

## Acceptance Criteria

- 1000+ files load smoothly
- Dashboard loads in <1s
- Large files (100KB+) edit smoothly
- Queries return in <500ms
- Memory usage stable

## Optimizations

### Frontend
- React.memo for expensive components
- Virtual list for file tree (react-virtual)
- Code splitting by route
- Image lazy loading

### Backend
- DuckDB indexes on common queries
- Query result caching (TTL-based)
- Streaming responses for large data
- Background job queue (extraction)

### Database
```sql
CREATE INDEX idx_exercise_date ON exercise_log(date);
CREATE INDEX idx_metrics_date ON daily_metrics(date);
CREATE INDEX idx_extraction_path ON extraction_log(file_path);
```

## Benchmarks to Track

- Time to first paint
- File tree render time
- Search latency (p50, p99)
- Extraction throughput
