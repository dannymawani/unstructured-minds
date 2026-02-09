# 02 - Authentication & User Management

## Provider: Clerk

[clerk.com](https://clerk.com) - Drop-in authentication for React + Python.

### Why Clerk Over Alternatives

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Clerk** | Best React DX, pre-built components, webhooks, free 10K MAU | Vendor lock-in | **Winner** |
| Auth0 | Mature, well-documented | Complex setup, expensive past free tier | Good but overkill |
| Supabase Auth | Free, pairs with Supabase DB | Weaker React components, more DIY | Runner-up |
| NextAuth/Auth.js | OSS, flexible | Requires Next.js (we use Vite) | Doesn't fit |
| Firebase Auth | Free tier, Google native | Google ecosystem lock-in, firestore push | Not ideal |
| DIY (OAuth + JWT) | Full control | Months of work, security risk | No |

### Social Login Providers (Phase 1)

1. **Google** - Primary. Most users will use this. Also gives us Google Drive access.
2. **Email/password** - Fallback for users who don't want social login.

### Social Login Providers (Phase 2)

3. **Apple** - Required if we ever do iOS.
4. **GitHub** - Developer audience.

## Frontend Integration

### Install

```bash
npm install @clerk/clerk-react
```

### Wrap App

```tsx
// main.tsx
import { ClerkProvider } from '@clerk/clerk-react'

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ClerkProvider publishableKey={CLERK_KEY}>
    <App />
  </ClerkProvider>
)
```

### Protected Routes

```tsx
// App.tsx
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react'

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/pricing" element={<PricingPage />} />

      {/* Protected app routes */}
      <Route path="/app/*" element={
        <>
          <SignedIn>
            <AppLayout />
          </SignedIn>
          <SignedOut>
            <RedirectToSignIn />
          </SignedOut>
        </>
      } />
    </Routes>
  )
}
```

### API Calls with Auth Token

```tsx
// lib/apiClient.ts (modified)
import { useAuth } from '@clerk/clerk-react'

// In a hook or component:
const { getToken } = useAuth()

const apiCall = async (path: string, options?: RequestInit) => {
  const token = await getToken()
  return fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })
}
```

### Sign In / Sign Up Pages

Clerk provides pre-built components. We can customize the theme to match our brand.

```tsx
import { SignIn } from '@clerk/clerk-react'

function LoginPage() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-950">
      <SignIn
        appearance={{
          variables: {
            colorPrimary: '#14b8a6',        // Our teal
            colorBackground: '#1e293b',      // Slate-800
            colorText: '#f8fafc',            // Slate-50
            colorInputBackground: '#0f172a', // Slate-900
          }
        }}
      />
    </div>
  )
}
```

## Backend Integration

### Install

```bash
pip install clerk-backend-api pyjwt[crypto]
```

### Auth Middleware

```python
# backend/src/middleware/auth.py
from fastapi import Request, HTTPException
from functools import wraps
import jwt
import httpx

CLERK_JWKS_URL = "https://{your-clerk-domain}/.well-known/jwks.json"

class ClerkAuthMiddleware:
    """Verify Clerk JWT on every API request."""

    def __init__(self):
        self._jwks = None

    async def get_jwks(self):
        if not self._jwks:
            async with httpx.AsyncClient() as client:
                resp = await client.get(CLERK_JWKS_URL)
                self._jwks = resp.json()
        return self._jwks

    async def verify_token(self, request: Request) -> str:
        """Returns user_id or raises 401."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing auth token")

        token = auth_header.split(" ")[1]
        jwks = await self.get_jwks()

        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                options={"verify_aud": False}
            )
            return payload["sub"]  # Clerk user ID
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")


# Dependency for route handlers
async def get_current_user(request: Request) -> str:
    auth = ClerkAuthMiddleware()
    return await auth.verify_token(request)
```

### Use in Routes

```python
from fastapi import Depends
from middleware.auth import get_current_user

@router.post("/vault/file")
async def save_file(
    user_id: str = Depends(get_current_user),
    # ... other params
):
    # user_id is guaranteed to be authenticated
    vault = get_user_vault(user_id)  # Google Drive for this user
    db = get_user_db(user_id)        # DuckDB for this user
    ...
```

## Google OAuth Scopes

When users sign in with Google through Clerk, we request additional OAuth scopes for Google Drive access.

```
openid                          # Standard OIDC
email                           # User's email
profile                         # Name, avatar
https://www.googleapis.com/auth/drive.file  # Files created by our app only
```

The `drive.file` scope is important: it only grants access to files our app creates, NOT the user's entire Drive. This is the least-privilege approach and builds trust.

### Storing Google OAuth Tokens

Clerk stores the Google OAuth access/refresh tokens for us. We retrieve them server-side:

```python
# Get Google Drive token for a user
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)
oauth_tokens = clerk.users.get_o_auth_access_token(
    user_id=user_id,
    provider="oauth_google"
)
google_access_token = oauth_tokens[0].token
```

## User Data Model (Supabase)

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,              -- Clerk user ID (e.g., user_2x...)
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,
    google_drive_folder_id TEXT,      -- Root folder in their Drive
    tier TEXT DEFAULT 'free',          -- free, pro, enterprise
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ
);

CREATE TABLE usage_log (
    id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    action TEXT NOT NULL,              -- 'extraction', 'query', 'note_assist'
    model TEXT NOT NULL,               -- 'haiku-4.5', 'sonnet-4.5'
    input_tokens INT,
    output_tokens INT,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    settings JSONB DEFAULT '{}',       -- Mirrors current settings.json
    schemas JSONB DEFAULT '{}',        -- Custom extraction schemas
    anthropic_api_key TEXT,            -- User's own key (encrypted, optional)
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Webhook: Provision New Users

```python
# POST /webhooks/clerk
async def handle_clerk_webhook(request: Request):
    payload = await request.json()

    if payload["type"] == "user.created":
        user = payload["data"]
        user_id = user["id"]
        email = user["email_addresses"][0]["email_address"]

        # 1. Create user in Supabase
        await supabase.table("users").insert({
            "id": user_id,
            "email": email,
            "name": f"{user['first_name']} {user['last_name']}",
            "avatar_url": user.get("image_url"),
        }).execute()

        # 2. Create empty DuckDB with schema
        await provision_user_database(user_id)

        # 3. Create Google Drive folder
        folder_id = await create_drive_folder(user_id)
        await supabase.table("users").update(
            {"google_drive_folder_id": folder_id}
        ).eq("id", user_id).execute()

        # 4. Create welcome note
        await create_welcome_note(user_id, folder_id)
```

## Session Management

- **Session duration**: 7 days (Clerk default, configurable)
- **Token refresh**: Clerk SDK handles automatically
- **Multi-device**: Supported out of the box
- **Sign out**: Clerk `<UserButton />` component includes sign out
