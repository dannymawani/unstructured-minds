# 01 - Multi-Tenant Architecture

## Current State (Single User)

```
React SPA ──> FastAPI ──> Local DuckDB file
                 |
              Local vault/ directory (markdown files)
              Single .env with one ANTHROPIC_API_KEY
```

Everything runs on one machine. One user. One database. One vault.

## Target State (Multi-Tenant)

```
Vercel (React SPA)
    │
    ├── Clerk SDK (auth, session tokens)
    │
    └── Railway (FastAPI)
            │
            ├── Supabase Postgres ──── User accounts, usage tracking, billing
            │
            ├── Cloudflare R2 / S3 ── Per-user DuckDB files
            │                          (user_123.duckdb, user_456.duckdb)
            │
            ├── Google Drive API ───── Per-user markdown files
            │                          (notes stored in user's own Drive)
            │
            └── Anthropic API ──────── Proxied through our backend
                                       (usage metered per user)
```

## What Changes

### Frontend (Minimal Changes)

| Area | Current | New |
|------|---------|-----|
| Auth | None | Clerk React SDK wraps app |
| API calls | Direct to `localhost:8000` | Include Clerk session token in headers |
| Routes | All public | Protected routes behind `<SignedIn>` |
| Landing | None | New `/` route with marketing page |
| App entry | `/` | Moves to `/app` |

The Milkdown editor, dashboard, kanban, chat - all stay the same. We just gate access behind login.

### Backend (Moderate Changes)

| Area | Current | New |
|------|---------|-----|
| Auth middleware | None | Verify Clerk JWT on every request |
| DuckDB connection | Single file | Load user-specific `.duckdb` from R2 |
| Vault path | Single `./vault/` | Google Drive API per user |
| File operations | Local filesystem | Google Drive read/write |
| Config | Single `.env` | Per-user settings in Supabase |
| Rate limiting | IP-based | User-based with usage tracking |

### Data Layer (Significant Changes)

| Component | Current | New |
|-----------|---------|-----|
| DuckDB | `data/unstructured.duckdb` | `r2://duckdb/{user_id}.duckdb` |
| Vault files | `vault/*.md` | Google Drive (user's account) |
| Settings | `data/settings.json` | Supabase `user_settings` table |
| Schemas | `data/schemas/*.json` | Shared defaults + per-user overrides |
| Exercise defs | `data/exercise_definitions.json` | Shared defaults + per-user overrides |

## Key Design Decisions

### 1. DuckDB Per-User (Not Shared Postgres)

Why not just put everyone in one big Postgres database?

- **Isolation**: One user's data can never leak to another. No `WHERE user_id = ?` bugs.
- **Performance**: Each user's queries run against only their data. No noisy neighbors.
- **Portability**: Users can export/download their entire database file.
- **Familiarity**: The existing extraction pipeline, query engine, and dashboard all work against DuckDB unchanged.
- **Cost**: DuckDB files are small (most users will be <50MB). R2 storage is $0.015/GB/month.

Trade-off: We need to load/unload DuckDB files per request. Mitigation: LRU cache of recently-accessed databases in memory on Railway.

### 2. Google Drive for Files (Not Our Storage)

Why not store markdown files ourselves?

- **Zero storage cost**: Users store files in their own Google Drive.
- **Familiarity**: Users can browse/edit their notes in Google Drive if they want.
- **Trust**: "Your notes live in YOUR Google Drive" is a strong privacy story.
- **Sync**: Changes in Google Drive can trigger webhooks for re-extraction.
- **Backup**: Google Drive is their backup. We don't need to manage it.

Trade-off: Google Drive API has rate limits and latency. Mitigation: Cache recent files in Redis on Railway.

### 3. Clerk for Auth (Not DIY)

Why not build auth ourselves?

- **Speed**: Clerk gives us Google login in ~30 minutes of integration work.
- **Security**: Auth is hard to get right. Clerk handles token rotation, session management, CSRF.
- **UI**: Clerk provides pre-built login/signup components that look professional.
- **Webhooks**: Clerk fires events on signup/login that we use to provision user resources.
- **Free tier**: 10,000 MAU free.

## Request Flow (Authenticated)

```
1. User visits app.unstructuredminds.com
2. Clerk SDK checks session → redirect to login if needed
3. User clicks "Sign in with Google"
4. Clerk handles OAuth flow → returns session token
5. Frontend stores session → includes in API headers
6. POST /api/vault/file { Authorization: Bearer <clerk_token> }
7. Backend middleware:
   a. Verify Clerk JWT → extract user_id
   b. Load user's DuckDB from R2 cache
   c. Resolve user's Google Drive credentials
   d. Process request (read/write file, extract data, query)
   e. Save updated DuckDB back to R2
   f. Log usage to Supabase
8. Return response to frontend
```

## Tenant Provisioning (On First Login)

When Clerk fires a `user.created` webhook:

1. Create row in Supabase `users` table
2. Create empty DuckDB file with schema, upload to R2
3. Create "Unstructured Minds" folder in user's Google Drive
4. Create default settings and schemas
5. Create a welcome daily note in their Drive
6. Grant free tier usage quota

## Scaling Considerations

| Users | DuckDB Strategy | Backend |
|-------|----------------|---------|
| 1-100 | Load from R2 on demand, LRU cache (10 in memory) | 1 Railway instance |
| 100-1K | Larger LRU cache, async pre-warming | 2 Railway instances |
| 1K-10K | DuckDB files cached on attached SSD | Dedicated compute |
| 10K+ | Consider DuckDB-WASM in browser for reads | Horizontal scaling |

The beauty of per-user DuckDB: scaling is linear and predictable. No shared database bottleneck.
