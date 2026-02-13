---
name: backup
description: Pull cloud Postgres data back to local DuckDB, vault files, and JSON settings
disable-model-invocation: true
allowed-tools: Bash(python3 -m scripts.backup_to_local *)
---

# Backup from Cloud

One-command backup that pulls Postgres data back to local storage. The reverse of `/setup-cloud`.

## What It Does

1. **Safety backup** — timestamped copy of existing `.duckdb` file
2. **Pull data tables** — 9 tables from Postgres → local DuckDB (strips `user_id`)
3. **Pull community exercises** — global exercise pool (no user_id filter)
4. **Pull vault files** — `vault_files` table → local `vault/` directory
5. **Pull JSON settings** — `user_settings` table → local `data/*.json` files
6. **Verify** — print DuckDB row counts

## Commands

```bash
# Full backup (all data + vault + settings)
cd backend && python3 -m scripts.backup_to_local

# Data tables only
cd backend && python3 -m scripts.backup_to_local --tables-only

# Vault files only
cd backend && python3 -m scripts.backup_to_local --vault-only

# JSON settings only
cd backend && python3 -m scripts.backup_to_local --settings-only
```

## Execution

1. Parse $ARGUMENTS:
   - No args or `full`: run full backup
   - `tables`: run with `--tables-only`
   - `vault`: run with `--vault-only`
   - `settings`: run with `--settings-only`
   - Pass through any other flags directly

2. Run from `backend/` directory:
```bash
cd backend && python3 -m scripts.backup_to_local $FLAGS
```

3. Report results: rows pulled, files written, verification summary.

## Prerequisites

- `DATABASE_URL` must be set in `.env` (project root)
- Postgres server must be reachable

## Arguments

$ARGUMENTS
