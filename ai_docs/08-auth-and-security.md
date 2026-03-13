# Auth & Security

Clerk authentication, JWT flow, security headers, SQL validation, and testing auth bypass.

## Auth Modes

| Mode | Auth | User ID Source |
|------|------|---------------|
| Local (`USE_CLOUD=false`) | Disabled | `LOCAL_USER_ID = "local"` (hardcoded) |
| Cloud (`USE_CLOUD=true` + `DATABASE_URL`) | Clerk JWT | `uuid5(NAMESPACE_URL, clerk_sub)` |

There is no `DEFAULT_USER_ID` — local mode has one hardcoded user, cloud mode derives identity from JWT.

## Auth Flow (Cloud Mode)

```
Frontend                     Backend
   │                            │
   ├─ Clerk getToken() ────────►│ Authorization: Bearer <JWT>
   │                            │
   │                            ├─ verify_clerk_token()
   │                            │   ├─ Extract JWT, get kid
   │                            │   ├─ Fetch JWKS (cached 1h)
   │                            │   ├─ Verify RSA signature
   │                            │   └─ Decode payload
   │                            │
   │                            ├─ get_user_id()
   │                            │   ├─ payload["sub"] (Clerk ID)
   │                            │   ├─ uuid5(NAMESPACE_URL, sub)
   │                            │   └─ Seed analytics cache if first request
   │                            │
   │                            └─ All DB queries include WHERE user_id = ?
```

### User ID Mapping

```python
CLERK_NAMESPACE = uuid.UUID("6ba7b811-6ba5-11d1-80b6-00c04fd430c8")  # NAMESPACE_URL
user_id = str(uuid.uuid5(CLERK_NAMESPACE, clerk_jwt_payload["sub"]))
# e.g., "user_39XgYzwinap2GxAmggtHgU0ACa9" -> "4e866c49-1e83-5366-b93f-3f92b14803b4"
```

## Frontend Auth Components

| File | Role |
|------|------|
| `main.tsx` | Wraps app in `<ClerkProvider>` when `VITE_CLERK_PUBLISHABLE_KEY` is set |
| `App.tsx` | `<SignedIn>` / `<SignedOut>` gates; `<AuthTokenSync>` registers token getter |
| `lib/apiClient.ts` | Token gating + global `fetch` interceptor for auth headers |

**Token injection flow:**
1. `apiClient.ts` creates a `_tokenReady` Promise at module load
2. If Clerk disabled, resolves immediately
3. When Clerk enabled, `AuthTokenSync` calls `setTokenGetter(getToken)` which resolves the Promise
4. A **global `window.fetch` interceptor** catches ALL fetch calls to `API_BASE_URL` and injects `Authorization: Bearer` header

## Backend Auth Components

| File | Role |
|------|------|
| `config.py` | `LOCAL_USER_ID` constant; `auth_enabled` = `is_cloud_mode` |
| `middleware/clerk_auth.py` | `verify_clerk_token()` — JWKS fetch, RSA verify, decode |
| `api/dependencies.py` | `get_user_id()` — local: `LOCAL_USER_ID`; cloud: JWT → UUID |

### JWKS Caching

Backend caches Clerk's JWKS public keys in memory. On key rotation (unknown `kid`), clears cache and retries once. No TTL — cache lives for process lifetime.

## Configuration

| Env Var | Where | Purpose |
|---------|-------|---------|
| `VITE_CLERK_PUBLISHABLE_KEY` | Frontend (build arg) | Enables Clerk UI, sign-in gate |
| `CLERK_SECRET_KEY` | Backend | JWT validation (JWKS fetch) |
| `CLERK_DOMAIN` | Backend | JWKS URL + JWT issuer validation |

## Security Measures

### SQL Validation (Defense-in-Depth)

4-layer defense for AI-generated SQL via `/query/natural`:

1. **System prompt separation** — SQL generation uses `system` parameter with anti-injection rules
2. **`validate_sql()`** — Keyword deny-list + function deny-list + system table blocking + DuckDB parser (exactly 1 statement)
3. **`read_only_execute()`** — Wraps in `BEGIN TRANSACTION` / `ROLLBACK`, materializes results before rollback
4. **Auto LIMIT 100** on all results

### Rate Limiting

Per-endpoint limits via slowapi:
- Extraction: 20/min
- Queries: 30/min
- Search: 100/min
- Export/Import: 5/min

### Security Headers

Defined in `frontend/nginx/security-headers.conf`:
- Content-Security-Policy (CSP)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

**Important:** CSP lives in `nginx/security-headers.conf`, `include`d from `nginx.conf` in both server block and `location = /index.html` block (nginx doesn't inherit `add_header` from parent when child uses `add_header`). Update CSP in one place only.

### CORS

Configured origins: `http://localhost:3000,http://localhost:5173`. Configurable via `CORS_ORIGINS` env var.

### Input Validation

- Pydantic models for all request bodies
- Max 255 char paths, no `..` traversal
- Type and constraint validation on all fields

### Middleware Stack

**Order:** RequestLogging → SecurityHeaders → CORS → RateLimiting

## Testing Auth Bypass

The dev `.env` has Clerk/Postgres credentials, so `settings` has `auth_enabled=True`. Tests bypass via autouse fixture in `backend/tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def disable_auth():
    # 1. DI override for Depends(get_user_id)
    app.dependency_overrides[get_user_id] = lambda: LOCAL_USER_ID

    # 2. Patch settings in dependencies.py
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.auth_enabled = False
        mock_settings.is_cloud_mode = False
        yield
```

**Why patch `dependencies.settings`?** Dependency functions call each other directly (not through DI), so patching forces local-mode paths:
- `get_storage()` → `is_cloud_mode=False` → returns `request.app.state.storage`
- `get_datastore()` → `is_cloud_mode=False` → returns `request.app.state.datastore`
- `get_user_id()` → `is_cloud_mode=False` → returns `LOCAL_USER_ID`

Individual test files that need custom settings patch their own router modules on top.

## Known Limitations

- Local mode has **no authentication** — designed for single-user local/private network use
- **No encryption at rest** — use full-disk encryption if needed
- API key stored in environment variable (not encrypted)
- If exposing to network, place behind reverse proxy with authentication
