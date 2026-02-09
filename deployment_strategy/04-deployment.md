# 04 - Deployment

## Stack

```
┌──────────────────────────────────────────────────────┐
│  Vercel          → Frontend (React SPA)              │
│  Railway         → Backend (FastAPI + Python)        │
│  Supabase        → Postgres (users, usage, settings) │
│  Cloudflare R2   → Object storage (DuckDB files)     │
│  Upstash Redis   → Caching (Drive files, sessions)   │
│  Clerk           → Authentication                    │
│  Cloudflare      → DNS + CDN                         │
└──────────────────────────────────────────────────────┘
```

## Why This Stack

| Choice | Reason |
|--------|--------|
| **Vercel** for frontend | You asked for it. Perfect for Vite/React SPAs. Free tier handles 100K visitors/month. |
| **Railway** for backend | Easiest way to deploy Docker containers. Native Python support. $5/mo hobby plan. Scales up simply. |
| **Supabase** for Postgres | Free 500MB database. Great dashboard. Real-time subscriptions if we want them later. |
| **Cloudflare R2** for storage | S3-compatible, zero egress fees. 10GB free. Perfect for DuckDB files. |
| **Upstash Redis** for cache | Serverless Redis. Free 10K commands/day. Good for caching Drive API responses. |

### Why Not Just Vercel for Everything?

Vercel's serverless functions are Node.js-oriented. Our backend is Python + FastAPI + DuckDB, which needs:
- Persistent filesystem (for DuckDB connections)
- Long-running processes (extraction pipelines can take 10-30s)
- WebSocket/SSE support (for streaming AI responses)

Vercel's serverless functions have a 10s timeout on free tier and no persistent disk. Railway gives us a real server.

## Domain Setup

```
unstructuredminds.com          → Vercel (landing page + app)
api.unstructuredminds.com      → Railway (FastAPI backend)
```

### DNS Records (Cloudflare)

```
Type  Name   Value                          Proxy
A     @      76.76.21.21 (Vercel)          Yes
CNAME www    cname.vercel-dns.com           Yes
CNAME api    your-app.up.railway.app        Yes (or DNS-only)
```

## Vercel Setup (Frontend)

### 1. Connect Repository

```bash
# Install Vercel CLI
npm i -g vercel

# From project root
cd frontend
vercel
```

Or connect via Vercel dashboard → Import Git Repository → Select `unstructured_minds`.

### 2. Build Settings

```json
// vercel.json (in frontend/ directory)
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm install",
  "framework": "vite",
  "rewrites": [
    { "source": "/app/(.*)", "destination": "/index.html" },
    { "source": "/pricing", "destination": "/index.html" },
    { "source": "/login", "destination": "/index.html" }
  ]
}
```

### 3. Environment Variables (Vercel Dashboard)

```
VITE_API_URL=https://api.unstructuredminds.com
VITE_CLERK_PUBLISHABLE_KEY=pk_live_...
```

### 4. Deploy

```bash
# Preview deploy
vercel

# Production deploy
vercel --prod
```

Every push to `main` auto-deploys. PRs get preview URLs.

## Railway Setup (Backend)

### 1. Create Project

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project (from backend/ directory)
cd backend
railway init
```

### 2. Configuration

Railway reads `Dockerfile` automatically. Our existing `backend/Dockerfile` works as-is.

### 3. Environment Variables (Railway Dashboard)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...
CLERK_SECRET_KEY=sk_live_...
CLERK_WEBHOOK_SECRET=whsec_...

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...

# Cloudflare R2
R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET=unstructured-minds

# Upstash Redis
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# App
CORS_ORIGINS=https://unstructuredminds.com,https://www.unstructuredminds.com
DEBUG=false
LOG_LEVEL=INFO
```

### 4. Custom Domain

In Railway dashboard: Settings → Domains → Add `api.unstructuredminds.com`

### 5. Deploy

```bash
# Railway auto-deploys from git, or manually:
railway up
```

## Supabase Setup

### 1. Create Project

Go to [supabase.com](https://supabase.com) → New Project → Name it "unstructured-minds".

### 2. Run Migrations

```sql
-- Run in Supabase SQL Editor
-- (tables defined in 03-data-strategy.md)
```

### 3. Get Connection Info

From Supabase dashboard → Settings → API:
- `SUPABASE_URL`: `https://xxx.supabase.co`
- `SUPABASE_KEY`: `eyJhbGc...` (service role key for backend)

## Cloudflare R2 Setup

### 1. Create Bucket

Cloudflare Dashboard → R2 → Create Bucket → Name: `unstructured-minds`

### 2. Generate API Token

R2 → Manage R2 API Tokens → Create Token
- Permissions: Object Read & Write
- Bucket: `unstructured-minds`

### 3. Save Credentials

```
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<from token creation>
R2_SECRET_ACCESS_KEY=<from token creation>
R2_BUCKET=unstructured-minds
```

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Backend tests
        run: |
          cd backend
          pip install -e ".[dev]"
          pytest

      - name: Frontend tests
        run: |
          cd frontend
          npm ci
          npm test

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: frontend
          vercel-args: '--prod'

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: backend
```

## Health Monitoring

### Uptime Checks

Use [BetterUptime](https://betteruptime.com) (free tier) or Railway's built-in health checks:

```
https://api.unstructuredminds.com/health  → Should return 200
https://unstructuredminds.com             → Should return 200
```

### Logging

- **Backend**: structlog → Railway's log viewer (already configured)
- **Frontend**: Vercel's log viewer for build/deploy logs
- **Errors**: Add Sentry later (free tier: 5K events/month)

## SSL/TLS

- **Vercel**: Automatic SSL for custom domains
- **Railway**: Automatic SSL for custom domains
- **Cloudflare**: Automatic SSL for DNS-proxied domains

Zero SSL configuration needed.

## Scaling Path

| Phase | Users | Frontend | Backend | Cost |
|-------|-------|----------|---------|------|
| Launch | 1-100 | Vercel Free | Railway Hobby ($5/mo) | ~$10/mo |
| Growth | 100-1K | Vercel Free | Railway Pro ($20/mo) | ~$50/mo |
| Scale | 1K-10K | Vercel Pro ($20/mo) | Railway Team | ~$200/mo |
| Big | 10K+ | Vercel Enterprise | Multiple Railway services | Custom |

The beauty: no infrastructure changes between phases. Just upgrade plans.
