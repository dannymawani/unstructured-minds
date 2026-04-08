# Authentication Architecture

## Overview

Unstructured Minds has two modes with clean auth boundaries:

- **Local mode** (`STORAGE_MODE=local`): DuckDB + filesystem, zero auth, single implicit user (`LOCAL_USER_ID = "local"`)
- **Postgres mode** (`STORAGE_MODE=postgres` + `DATABASE_URL`): Postgres + optional auth (none/basic/clerk)

There is no `DEFAULT_USER_ID` — in cloud mode identity comes from Clerk; in local mode there's one hardcoded user.

## Flow

```
Browser                     Frontend (React)              Backend (FastAPI)           Clerk
  |                              |                              |                      |
  |--- open app --------------->|                              |                      |
  |                              |--- ClerkProvider init ------>|                      |
  |                              |<-- session loaded -----------|                      |
  |                              |                              |                      |
  |  (SignedOut gate)            |                              |                      |
  |--- click "Sign In" -------->|--- redirect to Clerk ------->|                      |
  |                              |                              |<-- JWT issued --------|
  |                              |<-- SignedIn renders ---------|                      |
  |                              |                              |                      |
  |  (AuthTokenSync effect)      |                              |                      |
  |                              |--- setTokenGetter(getToken) -|                      |
  |                              |--- _tokenReady resolves -----|                      |
  |                              |                              |                      |
  |  (API calls now unblocked)   |                              |                      |
  |                              |--- GET /settings             |                      |
  |                              |    Authorization: Bearer JWT |                      |
  |                              |                              |--- verify JWT ------->|
  |                              |                              |<-- JWKS public key ---|
  |                              |                              |                      |
  |                              |                              |--- uuid5(sub) ------->|
  |                              |                              |--- query Postgres     |
  |                              |                              |    WHERE user_id = ?  |
  |                              |<-- 200 user-scoped data -----|                      |
```

## Components

### Frontend

| File | Role |
|------|------|
| `main.tsx` | Wraps app in `<ClerkProvider>` when `VITE_CLERK_PUBLISHABLE_KEY` is set |
| `App.tsx` | `<SignedIn>` / `<SignedOut>` gates; `<AuthTokenSync>` registers token getter |
| `lib/apiClient.ts` | Token gating + global `fetch` interceptor for auth headers |

**How token injection works:**

1. `apiClient.ts` creates a `_tokenReady` Promise at module load
2. If Clerk is disabled (`VITE_CLERK_PUBLISHABLE_KEY` not set), resolves immediately
3. When Clerk is enabled, `AuthTokenSync` calls `setTokenGetter(getToken)` which resolves the Promise
4. A **global `window.fetch` interceptor** catches ALL fetch calls to `API_BASE_URL` and injects `Authorization: Bearer <token>` headers
5. This covers both the `api` module AND the 50+ direct `fetch()` calls across 28 components

### Backend

| File | Role |
|------|------|
| `config.py` | `LOCAL_USER_ID` constant; `auth_enabled` checks `auth_mode != "none"` or (cloud mode + Clerk secrets) |
| `middleware/clerk_auth.py` | `verify_clerk_token()` — fetches JWKS from Clerk, verifies RS256 JWT, returns payload |
| `api/dependencies.py` | `get_user_id()` — local: returns `LOCAL_USER_ID`; cloud: verifies JWT, maps `sub` to UUID |

**User ID mapping (cloud mode):**

```python
CLERK_NAMESPACE = uuid.UUID("6ba7b811-6ba5-11d1-80b6-00c04fd430c8")  # NAMESPACE_URL
user_id = str(uuid.uuid5(CLERK_NAMESPACE, clerk_jwt_payload["sub"]))
# e.g., "user_39XgYzwinap2GxAmggtHgU0ACa9" -> "4e866c49-1e83-5366-b93f-3f92b14803b4"
```

All database queries are scoped by `user_id` in cloud mode.

### Configuration

| Env Var | Where | Purpose |
|---------|-------|---------|
| `VITE_CLERK_PUBLISHABLE_KEY` | Frontend | Enables Clerk UI, sign-in gate, token sync |
| `CLERK_SECRET_KEY` | Backend | Validates JWTs (fetches JWKS) — required for cloud mode |
| `CLERK_DOMAIN` | Backend | Clerk issuer domain for JWKS URL + JWT issuer validation — required for cloud mode |

### Modes

| Mode | Auth | User ID Source |
|------|------|---------------|
| Local (`STORAGE_MODE=local`) | Disabled | `LOCAL_USER_ID = "local"` (hardcoded) |
| Postgres (`STORAGE_MODE=postgres` + `DATABASE_URL`) | Configurable (none/basic/clerk) | `uuid5(NAMESPACE_URL, clerk_sub)` from JWT or `LOCAL_USER_ID` |

If cloud mode is active but Clerk credentials are missing, the first API request returns HTTP 500 with a clear error message.

## JWKS Caching

The backend caches Clerk's JWKS public keys in memory (`_jwks_cache`). On key rotation (unknown `kid` in JWT), it clears cache and retries once. No TTL — cache lives for the process lifetime.

## Testing

The dev `.env` has `CLERK_SECRET_KEY`, `CLERK_DOMAIN`, and `DATABASE_URL` set, so the real `settings` singleton has `auth_enabled=True` and `is_cloud_mode=True`. Without special handling, every test would hit the Clerk JWT verification path and fail with 401.

### How tests bypass auth

An **autouse fixture** in `backend/tests/conftest.py` (`disable_auth`) handles this globally:

```python
@pytest.fixture(autouse=True)
def disable_auth():
    # 1. DI override for endpoints using Depends(get_user_id)
    app.dependency_overrides[get_user_id] = lambda: LOCAL_USER_ID

    # 2. Patch the settings object in dependencies.py (where branching happens)
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.auth_enabled = False
        mock_settings.is_cloud_mode = False
        yield
```

**Why patch `dependencies.settings` specifically?** The dependency functions (`get_storage`, `get_datastore`, `get_user_id`) call each other directly — not through FastAPI's DI system — so the DI override alone doesn't reach them. Patching the `settings` object in that module forces the local-mode code path:

- `get_storage()` -> `is_cloud_mode=False` -> returns `request.app.state.storage`
- `get_datastore()` -> `is_cloud_mode=False` -> returns `request.app.state.datastore`
- `get_user_id()` -> `is_cloud_mode=False` -> returns `LOCAL_USER_ID`

Individual test files that need custom settings (e.g., `test_settings_api.py`) patch their own router modules on top of this.
