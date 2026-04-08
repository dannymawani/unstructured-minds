---
name: setup-cloud
description: Set up or reset cloud Postgres — create schemas, seed vault, migrate DuckDB data and JSON settings
disable-model-invocation: true
allowed-tools: Bash(python3 -m scripts.setup_cloud *)
---

# Cloud Setup

One-command setup/reset for cloud Postgres (Snowflake, Supabase, Neon, etc.).

## What It Does

1. **Drop tables** (optional, with `--drop-first`)
2. **Create schemas** — all 13 app tables + indexes
3. **Seed vault** — local `vault/` markdown files → `vault_files` table
4. **Migrate DuckDB** — extracted data (activities, exercises, metrics, food, tasks, reviews) → Postgres
5. **Migrate JSON settings** — settings.json, life_profile.json, training_config.json, ai_exercise_cache.json → `user_settings` table
6. **Verify** — print row counts for all tables

## Commands

```bash
# Full setup (schemas + all data)
cd backend && python3 -m scripts.setup_cloud

# Wipe and rebuild everything from scratch
cd backend && python3 -m scripts.setup_cloud --drop-first

# Schemas only (no data migration)
cd backend && python3 -m scripts.setup_cloud --skip-seed

# Custom paths
cd backend && python3 -m scripts.setup_cloud --vault-path /path/to/vault --data-path /path/to/data
```

## Execution

1. Parse $ARGUMENTS:
   - No args or `full`: run full setup (no drop)
   - `reset`: run with `--drop-first` (wipe + rebuild)
   - `schemas`: run with `--skip-seed`
   - Pass through any other flags directly

2. Run from `backend/` directory:
```bash
cd backend && python3 -m scripts.setup_cloud $FLAGS
```

3. Report results: tables created, rows migrated, verification summary.

## Prerequisites

- `DATABASE_URL` must be set in `.env` (project root)
- Postgres server must be reachable
- For DuckDB migration: `data/unstructured.duckdb` must exist locally

## Arguments

$ARGUMENTS
