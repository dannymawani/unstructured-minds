# Natural Language Query Interface

**Phase:** 4 - Advanced Features
**Priority:** High
**Status:** In Progress

## Description

Enable users to ask questions about their data in natural language and get intelligent responses backed by DuckDB queries.

## Tasks

- [ ] Query interpretation with Claude
- [ ] SQL generation from natural language
- [ ] Query result formatting
- [ ] Follow-up question handling
- [ ] Query history
- [ ] Suggested questions based on data

## Acceptance Criteria

- "How much did I sleep last week?" returns accurate data
- "Show my squat progress" generates chart-ready data
- Complex queries work (aggregations, comparisons)
- Invalid queries handled gracefully
- Results formatted in natural language

## Example Queries

- "How many hours did I sleep on average last month?"
- "What was my heaviest deadlift this year?"
- "Compare my mood on workout days vs rest days"
- "List all incomplete tasks from this week"

## Implementation

1. Claude interprets query intent
2. Generate safe parameterized SQL
3. Execute against DuckDB
4. Format results with Claude
5. Return structured response

## Key Files

- `backend/src/query/interpreter.py`
- `backend/src/query/sql_generator.py`
