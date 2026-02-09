# 03 - Data Strategy

## Principle: Users Own Their Data

Every piece of user data lives in infrastructure the user controls (Google Drive) or in isolated per-user storage (DuckDB on R2). There is no shared data lake where one user's data could leak to another.

## Three Data Stores

```
┌─────────────────────────────────────────────────┐
│                  Per-User Data                   │
├──────────────┬──────────────┬───────────────────┤
│ Google Drive │ DuckDB on R2 │ Supabase Postgres │
│ (notes)      │ (extracted)  │ (account)         │
├──────────────┼──────────────┼───────────────────┤
│ *.md files   │ activities   │ users             │
│ Daily-Notes/ │ exercise_log │ user_settings     │
│ Templates/   │ daily_metrics│ usage_log         │
│              │ food_log     │ subscriptions     │
│              │ tasks        │                   │
└──────────────┴──────────────┴───────────────────┘
     User owns      We host       We host
     (their Drive)  (isolated)    (shared DB)
```

## 1. Google Drive Integration

### Folder Structure (Created on Signup)

```
My Drive/
└── Unstructured Minds/          ← App-created root folder
    ├── Daily-Notes/
    │   ├── 2026-02/
    │   │   ├── 2026-02-01.md
    │   │   └── 2026-02-02.md
    │   └── 2026-03/
    ├── Templates/
    │   ├── daily-note.md
    │   ├── meeting.md
    │   └── workout.md
    └── Notes/
        ├── project-ideas.md
        └── reading-list.md
```

### API Operations

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class GoogleDriveVault:
    """Replaces local filesystem vault with Google Drive."""

    def __init__(self, access_token: str, root_folder_id: str):
        creds = Credentials(token=access_token)
        self.service = build('drive', 'v3', credentials=creds)
        self.root_folder_id = root_folder_id

    async def list_files(self, folder_path: str = "") -> list[dict]:
        """List markdown files in a folder."""
        folder_id = await self._resolve_path(folder_path)
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and mimeType='text/markdown'",
            fields="files(id, name, modifiedTime, size)"
        ).execute()
        return results.get('files', [])

    async def read_file(self, file_path: str) -> str:
        """Read a markdown file's content."""
        file_id = await self._resolve_path(file_path)
        content = self.service.files().get_media(fileId=file_id).execute()
        return content.decode('utf-8')

    async def write_file(self, file_path: str, content: str) -> None:
        """Create or update a markdown file."""
        # Check if file exists
        existing = await self._find_file(file_path)
        if existing:
            self.service.files().update(
                fileId=existing['id'],
                media_body=content.encode('utf-8')
            ).execute()
        else:
            folder_id = await self._ensure_folders(file_path)
            self.service.files().create(
                body={
                    'name': file_path.split('/')[-1],
                    'parents': [folder_id],
                    'mimeType': 'text/markdown'
                },
                media_body=content.encode('utf-8')
            ).execute()

    async def delete_file(self, file_path: str) -> None:
        """Move file to trash (not permanent delete)."""
        file_id = await self._resolve_path(file_path)
        self.service.files().update(
            fileId=file_id,
            body={'trashed': True}
        ).execute()
```

### Caching Layer

Google Drive API has latency (~200-500ms per call). We cache aggressively:

```python
class CachedDriveVault:
    """Wraps GoogleDriveVault with Redis caching."""

    def __init__(self, drive: GoogleDriveVault, redis: Redis, user_id: str):
        self.drive = drive
        self.redis = redis
        self.user_id = user_id
        self.ttl = 300  # 5 minutes

    async def read_file(self, path: str) -> str:
        cache_key = f"vault:{self.user_id}:{path}"
        cached = await self.redis.get(cache_key)
        if cached:
            return cached.decode()

        content = await self.drive.read_file(path)
        await self.redis.set(cache_key, content, ex=self.ttl)
        return content

    async def write_file(self, path: str, content: str) -> None:
        await self.drive.write_file(path, content)
        # Invalidate cache
        cache_key = f"vault:{self.user_id}:{path}"
        await self.redis.set(cache_key, content, ex=self.ttl)

    async def invalidate_user_cache(self) -> None:
        """Clear all cached files for a user."""
        pattern = f"vault:{self.user_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

### Google Drive Webhooks (Change Notifications)

When users edit files directly in Google Drive, we need to know:

```python
# Register a webhook for the user's root folder
watch_response = service.files().watch(
    fileId=root_folder_id,
    body={
        'id': f'watch-{user_id}',
        'type': 'web_hook',
        'address': 'https://api.unstructuredminds.com/webhooks/drive',
        'expiration': int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
    }
).execute()

# When Drive notifies us of changes:
@router.post("/webhooks/drive")
async def handle_drive_change(request: Request):
    user_id = extract_user_from_channel(request.headers)
    # Invalidate cache and re-extract changed files
    await invalidate_and_reextract(user_id)
```

## 2. Per-User DuckDB on Cloudflare R2

### Why R2 (Not S3)

- **No egress fees**: S3 charges for data transfer out. R2 doesn't. Since we load/save DuckDB files frequently, this matters.
- **S3-compatible API**: Same code works with both.
- **$0.015/GB/month**: Cheap storage for small DuckDB files (10-100MB each).

### DuckDB Lifecycle

```
Request arrives
    │
    ▼
Check LRU cache (in-memory)
    │
    ├── HIT: Use cached connection
    │
    └── MISS:
        │
        ▼
    Download user_123.duckdb from R2
        │
        ▼
    Open DuckDB connection
        │
        ▼
    Process request (query, extract, etc.)
        │
        ▼
    If data changed: upload back to R2
        │
        ▼
    Keep in LRU cache (evict oldest if full)
```

### Implementation

```python
import duckdb
import boto3
from functools import lru_cache
from pathlib import Path
import tempfile

class UserDatabaseManager:
    """Manages per-user DuckDB files stored in R2."""

    def __init__(self, r2_client, bucket: str, cache_dir: str = "/tmp/duckdb_cache"):
        self.r2 = r2_client
        self.bucket = bucket
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._connections: dict[str, duckdb.DuckDBPyConnection] = {}

    def get_db(self, user_id: str) -> duckdb.DuckDBPyConnection:
        """Get or create a DuckDB connection for a user."""
        if user_id in self._connections:
            return self._connections[user_id]

        local_path = self.cache_dir / f"{user_id}.duckdb"

        if not local_path.exists():
            # Download from R2
            self.r2.download_file(
                self.bucket,
                f"duckdb/{user_id}.duckdb",
                str(local_path)
            )

        conn = duckdb.connect(str(local_path))
        self._connections[user_id] = conn
        return conn

    async def save_db(self, user_id: str) -> None:
        """Upload user's DuckDB back to R2."""
        local_path = self.cache_dir / f"{user_id}.duckdb"
        if local_path.exists():
            self.r2.upload_file(
                str(local_path),
                self.bucket,
                f"duckdb/{user_id}.duckdb"
            )

    async def provision_new_user(self, user_id: str) -> None:
        """Create a fresh DuckDB with schema for a new user."""
        local_path = self.cache_dir / f"{user_id}.duckdb"
        conn = duckdb.connect(str(local_path))

        # Apply the standard schema (same as current db/schema.py)
        from db.schema import initialize_schema
        initialize_schema(conn)

        conn.close()
        await self.save_db(user_id)
```

### LRU Eviction

```python
from collections import OrderedDict

class LRUDatabaseCache:
    """Keep N most recently used databases in memory."""

    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self._cache: OrderedDict[str, duckdb.DuckDBPyConnection] = OrderedDict()

    def get(self, user_id: str) -> duckdb.DuckDBPyConnection | None:
        if user_id in self._cache:
            self._cache.move_to_end(user_id)
            return self._cache[user_id]
        return None

    def put(self, user_id: str, conn: duckdb.DuckDBPyConnection) -> None:
        if user_id in self._cache:
            self._cache.move_to_end(user_id)
        else:
            if len(self._cache) >= self.max_size:
                # Evict oldest: close connection, save to R2
                evicted_id, evicted_conn = self._cache.popitem(last=False)
                evicted_conn.close()
                # Trigger async save to R2
        self._cache[user_id] = conn
```

## 3. Supabase Postgres (App-Level Data)

Shared database for things that aren't per-user content:

```sql
-- User accounts (synced from Clerk webhooks)
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,
    google_drive_folder_id TEXT,
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    anthropic_api_key_encrypted TEXT,   -- Optional BYO key
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ
);

-- Token usage tracking
CREATE TABLE usage_log (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    action TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Monthly aggregated usage (for billing/limits)
CREATE MATERIALIZED VIEW monthly_usage AS
SELECT
    user_id,
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS total_requests,
    SUM(input_tokens) AS total_input_tokens,
    SUM(output_tokens) AS total_output_tokens,
    SUM(cost_usd) AS total_cost_usd
FROM usage_log
GROUP BY user_id, DATE_TRUNC('month', created_at);

-- User settings (replaces settings.json)
CREATE TABLE user_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    settings JSONB DEFAULT '{}',
    custom_schemas JSONB DEFAULT '{}',
    exercise_definitions JSONB DEFAULT '{}',
    training_config JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Data Migration Path

For your existing data (the current single-user setup):

1. Your current `data/unstructured.duckdb` becomes `user_{your_id}.duckdb` in R2
2. Your current `vault/*.md` files get uploaded to your Google Drive
3. Your current `data/settings.json` moves to Supabase `user_settings`
4. Your current `data/schemas/` move to Supabase `user_settings.custom_schemas`

This is a one-time migration script - your data becomes the first tenant's data.

## Data Export

Users should always be able to leave:

```
GET /api/export/all
→ ZIP file containing:
  ├── vault/          (all markdown files from Drive)
  ├── data.duckdb     (their DuckDB file)
  ├── settings.json   (their settings)
  └── schemas/        (their custom schemas)
```

## Privacy & Security

- DuckDB files are encrypted at rest (R2 server-side encryption)
- Google Drive OAuth tokens stored encrypted in Clerk
- Anthropic API keys (BYO) encrypted with AES-256 before storing in Supabase
- No cross-user data access possible by design (separate DuckDB files, separate Drive folders)
- GDPR: User can request full data export or account deletion
- Account deletion: Remove Supabase row, delete R2 DuckDB file, revoke Drive permissions
