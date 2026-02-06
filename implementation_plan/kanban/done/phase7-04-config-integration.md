# Integrate Config Files

**Phase:** 7 - Data Integration
**Priority:** Medium
**Status:** Done
**Completed:** 2026-02-06
**Branch:** feature/data-integration
**Depends On:** phase7-01

## Description

Load exercise_definitions.json, training_config.json, and injury_config.json at backend startup. Use exercise definitions to resolve aliases during extraction. Use training config for contextual chat responses. Use injury config for exercise warnings.

## Tasks

- [x] Add config loading to backend startup (load from data/ directory)
- [x] Pass exercise_definitions.json to Claude during extraction (alias resolution)
- [x] Pass training_config.json to chat/query context
- [x] Pass injury_config.json as extraction constraint context
- [x] Add API endpoint to read/update configs
- [x] Write tests for config loading

## Acceptance Criteria

- Backend loads all 3 config files at startup
- Exercise extraction resolves aliases (e.g., "dodloft" -> "deadlift")
- Chat responses reference athlete profile from training_config
- Config API endpoints work

## Key Files

- `data/exercise_definitions.json`
- `data/training_config.json`
- `data/injury_config.json`
- `backend/src/main.py`
