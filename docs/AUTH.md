# Authentication Guide

Unstructured Minds supports three authentication modes. Choose the one that fits your deployment.

| Mode | Best for | Multi-user | Setup time |
|------|----------|------------|------------|
| `none` | Local / self-hosted | No | Zero |
| `basic` | Shared network / Tailscale | No | 1 minute |
| `clerk` | Multi-user / SaaS | Yes | 15 minutes |

Auth mode is set via the `AUTH_MODE` env var and is independent of storage mode — you can use any auth mode with either DuckDB (local) or Postgres.

---

## Mode 1: No Auth (`AUTH_MODE=none`)

The default. No login screen, no credentials. A single hardcoded user ID (`"local"`) is used for all data.

```env
AUTH_MODE=none
```

**When to use:** Local development, personal self-hosted instance, trusted network.

**What you get:** Direct access to the app at `http://localhost:3000`. No sign-in flow.

---

## Mode 2: Basic Auth (`AUTH_MODE=basic`)

Simple username/password gate using HTTP Basic Authentication. Protects the app behind a login prompt. All users share the same `"local"` user ID — this is access control, not multi-user.

### Setup

1. Choose a username and password
2. Add to your `.env`:

```env
AUTH_MODE=basic
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=your-secure-password
```

3. Restart: `docker compose up -d`

**When to use:** Exposing over Tailscale or a local network where you want a simple login gate.

**Limitations:** Single user only. Password stored in plaintext in `.env`. No session management — the browser caches credentials.

---

## Mode 3: Clerk Auth (`AUTH_MODE=clerk`)

Full managed authentication via [Clerk](https://clerk.com). Supports email/password, Google, GitHub, and other social logins. Each user gets their own data, isolated by a deterministic UUID derived from their Clerk user ID.

### Prerequisites

- A [Clerk](https://clerk.com) account (free tier supports up to 10,000 monthly active users)
- `STORAGE_MODE=postgres` with a `DATABASE_URL` (Clerk needs Postgres for multi-user data isolation)

### Step-by-step setup

#### 1. Create a Clerk application

1. Go to [dashboard.clerk.com](https://dashboard.clerk.com) and sign in
2. Click **Create application**
3. Name it (e.g., "Unstructured Minds")
4. Choose sign-in methods (email, Google, GitHub, etc.)
5. Click **Create**

#### 2. Get your credentials

From the Clerk dashboard, go to **API Keys** (left sidebar):

| Credential | Where to find | Example |
|-----------|---------------|---------|
| **Publishable key** | Shown on API Keys page | `pk_test_bW9y...` or `pk_live_...` |
| **Secret key** | Shown on API Keys page (click to reveal) | `sk_test_jALi...` or `sk_live_...` |
| **Domain** | Settings > Domains, or visible in the dashboard URL | `your-app-name.clerk.accounts.dev` |

> **Test vs Live keys:** Use `pk_test_` / `sk_test_` keys for development. Switch to `pk_live_` / `sk_live_` for production. Test mode shows a Clerk dev badge on the sign-in page.

#### 3. Configure your `.env`

```env
# Storage (required for multi-user)
STORAGE_MODE=postgres
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Auth
AUTH_MODE=clerk
CLERK_SECRET_KEY=sk_test_your_secret_key
CLERK_DOMAIN=your-app-name.clerk.accounts.dev

# Frontend (IMPORTANT: this is a build-time variable)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_publishable_key
```

#### 4. Rebuild and start

The `VITE_CLERK_PUBLISHABLE_KEY` is baked into the frontend JavaScript at build time. You **must** rebuild when changing it:

```bash
docker compose up -d --build
```

A regular `docker compose up -d` (without `--build`) will NOT pick up a changed Clerk key.

#### 5. Verify

1. Open `http://localhost:3000` — you should see the Clerk sign-in page
2. Sign in with one of your configured methods
3. Create a note — it will be stored under your user ID
4. Sign out and sign in as a different user — each user sees only their own data

### How user isolation works

When a user signs in via Clerk, their Clerk user ID (e.g., `user_39XgYzwinap2GxAmggtHgU0ACa9`) is converted to a deterministic UUID:

```
Clerk sub  ->  uuid5(NAMESPACE_URL, sub)  ->  4e866c49-1e83-5366-b93f-3f92b14803b4
```

All database queries are automatically scoped with `WHERE user_id = ?` so users can never see each other's data.

### Configuring social logins (Google, GitHub, etc.)

1. In Clerk dashboard, go to **User & Authentication > Social connections**
2. Toggle on the providers you want (Google, GitHub, etc.)
3. For Google: Clerk provides a shared OAuth app for development. For production, add your own OAuth credentials
4. For GitHub: Same — Clerk's dev app works immediately, add your own for production
5. No code changes needed — Clerk handles the OAuth flow

### Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| No sign-in page, app loads directly | `VITE_CLERK_PUBLISHABLE_KEY` not baked in | Rebuild: `docker compose up -d --build` |
| 401 on all API calls | `CLERK_SECRET_KEY` wrong or missing | Check `.env`, restart backend |
| "Clerk: publishable key not valid" in console | Wrong key or test/live mismatch | Verify key in Clerk dashboard |
| Sign-in works but data doesn't load | `CLERK_DOMAIN` mismatch | Must match the domain in Clerk dashboard |
| Works locally but not in Docker | Env var not passed to container | Check `docker compose config` output |

---

## Switching between modes

Edit your `.env` file and change `AUTH_MODE` (plus the required credentials for that mode), then restart:

```bash
# For none or basic — just restart
docker compose up -d

# For clerk — must rebuild (VITE_CLERK_PUBLISHABLE_KEY is baked at build time)
docker compose up -d --build
```

If you're also switching storage mode (e.g., from `local` to `postgres`), update `STORAGE_MODE` and `DATABASE_URL` in the same `.env` file. See `.env.example` for all available options.

Your local data (`./vault/` and `./data/`) is never touched when switching to Postgres mode — the two storage backends are completely independent.

---

## Architecture reference

For implementation details (JWT verification flow, JWKS caching, token injection, testing auth bypass), see [ai_docs/08-auth-and-security.md](../ai_docs/08-auth-and-security.md).
