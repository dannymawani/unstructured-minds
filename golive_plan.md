# Go-Live Plan — Unstructured Minds

**Domain:** unstructuredminds.com (marketing/landing) + app.unstructuredminds.com (application)
**Cloud:** Google Cloud Platform + Cloudflare (DNS/CDN/SSL)
**Target:** Production-ready SaaS with tiered AI usage, containerized deployment

---

## 1. Architecture Overview

```
                    Cloudflare (free)
                 DNS + CDN + SSL + DDoS
                         │
          ┌──────────────┴──────────────┐
          │                             │
  unstructuredminds.com        app.unstructuredminds.com
  (marketing / landing)         (React + FastAPI app)
          │                             │
   Cloud Storage bucket          Cloud Run service
   (static site hosting)     (backend + frontend containers)
                                        │
                              ┌─────────┼─────────┐
                              │         │         │
                        Secret Mgr  Supabase   Anthropic
                        (env vars)  (Postgres)  (Claude)
```

### Why Cloudflare + GCP (not pure GCP)

| Concern | GCP-only | Cloudflare + GCP |
|---------|----------|-----------------|
| CDN | Cloud CDN requires Global LB (~$18+/mo) | Free, global, automatic |
| DNS | Cloud DNS: $0.20/zone + $0.40/M queries | Free, unlimited queries |
| SSL | Google-managed certs (free, but needs LB) | Free, automatic, no LB needed |
| DDoS | Cloud Armor: free basic, paid rules | Free, robust, always-on |
| WAF | Cloud Armor WAF: paid | Free managed rulesets |
| Migration | Locked to GCP networking | Change origin IP to move providers |
| **Cost** | **+$20-40/mo for networking** | **$0** |

Cloudflare handles the entire edge layer for free. GCP only runs compute + secrets.

### GCP Services Used

| Service | Purpose | Cost |
|---------|---------|------|
| **Cloud Run** | Run backend + frontend containers | ~$0-10/mo (scale to zero) |
| **Artifact Registry** | Private Docker image registry | ~$1/mo |
| **Secret Manager** | Store env vars (single JSON secret) | ~$0.06/mo |
| **Cloud Storage** | Landing page hosting + backups | ~$0-1/mo |
| **Cloud Monitoring** | Logs, metrics, alerts | Free tier generous |
| **Estimated total** | | **~$2-12/mo** |

> With Cloudflare free handling DNS/CDN/SSL/DDoS, the GCP bill is just compute + storage.

---

## 2. Container Registry — Artifact Registry

Push both images to a private Artifact Registry repository.

### Setup

```bash
# Create repository (once)
gcloud artifacts repositories create unstructured-minds \
  --repository-format=docker \
  --location=europe-north1 \
  --description="Unstructured Minds container images"

# Authenticate Docker
gcloud auth configure-docker europe-north1-docker.pkg.dev

# Build, tag, push
docker build -t um-backend ./backend
docker tag um-backend europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/backend:latest
docker push europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/backend:latest

docker build -t um-frontend ./frontend
docker tag um-frontend europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/frontend:latest
docker push europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/frontend:latest
```

### GitHub Actions CI

```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: projects/PROJECT_NUM/locations/global/workloadIdentityPools/github/providers/github
    service_account: github-ci@PROJECT_ID.iam.gserviceaccount.com

- uses: google-github-actions/setup-gcloud@v2

- run: gcloud auth configure-docker europe-north1-docker.pkg.dev
- run: docker build -t europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/backend:${{ github.sha }} ./backend
- run: docker push europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/backend:${{ github.sha }}
```

Uses **Workload Identity Federation** — no service account keys stored in GitHub secrets.

---

## 3. Secrets Management — Secret Manager

Store all env vars as a **single JSON secret**. Cloud Run reads it at startup via its service account — no credentials in code or CI.

### Secret contents

```json
{
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "DATABASE_URL": "postgresql://...",
  "CLERK_SECRET_KEY": "sk_live_...",
  "CLERK_DOMAIN": "...",
  "USE_CLOUD": "true",
  "STRIPE_SECRET_KEY": "sk_live_...",
  "STRIPE_WEBHOOK_SECRET": "whsec_...",
  "RESEND_API_KEY": "re_..."
}
```

### Setup

```bash
# Create secret
echo '{"ANTHROPIC_API_KEY":"sk-ant-...","DATABASE_URL":"postgresql://..."}' | \
  gcloud secrets create um-prod --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding um-prod \
  --member="serviceAccount:PROJECT_NUM-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### How Cloud Run reads it

**Option A — Mount as env vars (recommended):**
```bash
gcloud run deploy um-backend \
  --set-secrets=ANTHROPIC_API_KEY=um-prod:latest \
  ...
```

**Option B — Single JSON blob parsed at boot:**
```bash
# In container entrypoint
SECRET=$(gcloud secrets versions access latest --secret=um-prod)
export ANTHROPIC_API_KEY=$(echo $SECRET | jq -r .ANTHROPIC_API_KEY)
# ... etc
```

### Identity flow (no stored credentials)

```
Cloud Run container starts
  → Requests metadata token from GCP runtime (automatic, no config)
  → Token grants access to Secret Manager
  → Env vars populated before app starts
  → App boots normally
```

---

## 4. Container Compute — Cloud Run

### Why Cloud Run

- **Scale to zero** — $0 when no traffic (nights, weekends)
- **No cluster management** — not Kubernetes, not VMs
- **Built-in HTTPS** — auto-provisioned `.run.app` URL
- **Deploy in seconds** — `gcloud run deploy --image ...`
- **Multi-container** — sidecar support for frontend + backend in one service

### Deployment

```bash
# Deploy backend
gcloud run deploy um-backend \
  --image=europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/backend:latest \
  --region=europe-north1 \
  --port=8000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-secrets=ANTHROPIC_API_KEY=um-prod:latest,DATABASE_URL=um-prod:latest,CLERK_SECRET_KEY=um-prod:latest,CLERK_DOMAIN=um-prod:latest,USE_CLOUD=um-prod:latest \
  --allow-unauthenticated

# Deploy frontend
gcloud run deploy um-frontend \
  --image=europe-north1-docker.pkg.dev/PROJECT_ID/unstructured-minds/frontend:latest \
  --region=europe-north1 \
  --port=80 \
  --memory=256Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --allow-unauthenticated
```

### Cloud Run settings

| Setting | Value | Why |
|---------|-------|-----|
| Region | `europe-north1` (Finland) | Close to Supabase EU, low latency |
| Min instances | 0 | Scale to zero, save money |
| Max instances | 3 | Prevent runaway costs |
| Memory | 1Gi (backend), 256Mi (frontend) | DuckDB cache needs RAM |
| CPU | 1 | Sufficient for early traffic |
| Concurrency | 80 (default) | FastAPI handles concurrent well |
| Timeout | 300s | Long extractions need time |

### Cold start mitigation

Scale-to-zero means occasional cold starts (~1-2s). Options:
- Set `--min-instances=1` for always-warm ($5-10/mo)
- Or accept cold starts for now — only affects first request after idle

---

## 5. Domain, DNS, CDN & SSL — Cloudflare

### Domain layout

| Record | Type | Value | Proxied | Purpose |
|--------|------|-------|---------|---------|
| `unstructuredminds.com` | CNAME | `c.storage.googleapis.com` | Yes (orange) | Landing page from Cloud Storage |
| `app.unstructuredminds.com` | CNAME | `um-frontend-xxxxx.europe-north1.run.app` | Yes (orange) | React app via Cloud Run |
| `api.unstructuredminds.com` | CNAME | `um-backend-xxxxx.europe-north1.run.app` | Yes (orange) | FastAPI backend via Cloud Run |
| `www` | CNAME | `unstructuredminds.com` | Yes | Redirect to apex |

### Cloudflare setup

1. **Point nameservers** — Register domain's NS records to Cloudflare
2. **Add DNS records** — As above, all proxied (orange cloud)
3. **SSL mode** — Full (Strict) — Cloudflare encrypts to Cloud Run's `.run.app` cert
4. **Cache rules** — Static assets (JS/CSS/images/fonts) cached at edge
5. **Page rules** — `www.unstructuredminds.com/*` → 301 redirect to `unstructuredminds.com`

### What Cloudflare free gives you

- Global CDN (300+ edge locations) — static assets served from nearest POP
- Automatic HTTPS with free SSL certificates
- DDoS protection (unlimited, unmetered)
- Managed WAF rulesets (basic)
- Bot management (basic)
- Web Analytics (privacy-friendly, no JS)
- 5 page rules

### Frontend API routing

The React app on `app.unstructuredminds.com` calls the backend. Two options:

**Option A — Separate subdomain (recommended):**
- Frontend: `app.unstructuredminds.com` → Cloud Run frontend
- Backend: `api.unstructuredminds.com` → Cloud Run backend
- Frontend `apiClient.ts` base URL: `https://api.unstructuredminds.com`
- CORS allows `app.unstructuredminds.com`

**Option B — Path-based routing via Cloudflare Worker:**
- `app.unstructuredminds.com/api/*` → Cloud Run backend
- `app.unstructuredminds.com/*` → Cloud Run frontend
- Single domain, no CORS needed
- Requires Cloudflare Workers (free tier: 100K requests/day)

---

## 6. Stripe Integration — Payment Tiers & Pricing

### Tier Design

| Tier | Monthly Price | AI Token Budget | Features | Stripe Product |
|------|-------------|----------------|----------|---------------|
| **Free** | €0 | 100K tokens (~50 extractions) | Haiku extraction, 10 NL queries/mo | No Stripe (default) |
| **Pro** | €5/mo | 2M tokens | Haiku + Sonnet, unlimited queries | `prod_pro` subscription |
| **Power** | €12/mo | 10M tokens | All models, priority, API access | `prod_power` subscription |

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Frontend   │────→│   Backend    │────→│    Stripe     │
│  Pricing UI  │     │  /billing/*  │     │  Checkout +   │
│  Usage bar   │     │  Webhooks    │     │  Customer     │
│              │     │  Quota MW    │     │  Portal       │
└─────────────┘     └──────────────┘     └───────────────┘
```

### What needs to change in the codebase

#### New database tables

```sql
-- Token usage tracking
CREATE TABLE user_usage (
    user_id UUID NOT NULL,
    month VARCHAR NOT NULL,          -- '2026-02'
    tokens_used BIGINT DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, month)
);

-- Stripe subscription state
CREATE TABLE user_subscriptions (
    user_id UUID PRIMARY KEY,
    stripe_customer_id VARCHAR NOT NULL,
    stripe_subscription_id VARCHAR,
    tier VARCHAR NOT NULL DEFAULT 'free',   -- free/pro/power
    period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### New API endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /billing/checkout` | Create Stripe Checkout Session → redirect to Stripe |
| `POST /billing/portal` | Create Stripe Customer Portal session (manage/cancel) |
| `POST /billing/webhook` | Stripe webhook receiver (subscription events) |
| `GET /billing/usage` | Current month's token usage + tier + budget remaining |

#### Backend middleware changes

```python
# Quota check middleware (runs before Claude API calls)
async def check_quota(user_id: str) -> None:
    tier = get_user_tier(user_id)          # from user_subscriptions
    budget = TIER_BUDGETS[tier]            # {free: 100K, pro: 2M, power: 10M}
    used = get_month_usage(user_id)        # from user_usage
    if used >= budget:
        raise HTTPException(429, "Monthly token budget exceeded")

# After each Claude API call
async def track_usage(user_id: str, response) -> None:
    tokens = response.usage.input_tokens + response.usage.output_tokens
    upsert_usage(user_id, current_month(), tokens)
```

#### Stripe webhook events to handle

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Create/update `user_subscriptions` row, set tier |
| `customer.subscription.updated` | Update tier if plan changed |
| `customer.subscription.deleted` | Set tier back to `free` |
| `invoice.payment_failed` | Flag user, optionally downgrade after grace period |

#### Frontend changes

| Component | What |
|-----------|------|
| Pricing page | 3-tier card layout on `unstructuredminds.com/pricing` |
| Settings > Billing | Current plan, usage bar, upgrade/manage buttons |
| Usage bar | Token usage / budget shown in sidebar or settings |
| Paywall modal | When free user hits limit: "Upgrade to Pro for unlimited queries" |

### Implementation phases

**Phase 1 (go-live):** Usage tracking only
- Add `user_usage` table
- Count tokens after each Claude call
- Show usage in settings
- Soft 429 when free tier exceeded
- No Stripe yet — everyone is "free"

**Phase 2 (monetization):** Stripe integration
- Create Stripe products + prices in dashboard
- Add `user_subscriptions` table
- Implement checkout + webhook + portal endpoints
- Middleware reads tier from DB
- Frontend pricing page + upgrade flow

**Phase 3 (growth):** Annual plans, team plans
- Annual discount (2 months free)
- Team/org billing via Stripe
- Usage-based overage pricing

---

## 7. Cost Summary

| Item | Monthly Cost |
|------|-------------|
| Cloud Run (2 services, low traffic) | $0-10 |
| Artifact Registry | ~$1 |
| Secret Manager | ~$0.06 |
| Cloud Storage (landing page + backups) | ~$0-1 |
| Cloudflare | $0 (free tier) |
| Domain renewal | ~$1 (amortized) |
| Clerk | $0 (free tier, 10K MAU) |
| Supabase | $0 (free) or $25 (Pro) |
| Anthropic API | Variable (pass-through via tiers) |
| **Total fixed** | **~$3-38/mo** |

---

## 8. Go-Live Sequence

### Week 1 — Infrastructure
- [ ] Create GCP project, enable APIs (Cloud Run, Artifact Registry, Secret Manager)
- [ ] Set up Workload Identity Federation for GitHub Actions
- [ ] Create Artifact Registry repository
- [ ] Build + push container images
- [ ] Create secret in Secret Manager (single JSON blob)
- [ ] Deploy Cloud Run services (backend + frontend)
- [ ] Verify `.run.app` URLs work

### Week 2 — Domain & Networking
- [ ] Point `unstructuredminds.com` nameservers to Cloudflare
- [ ] Add DNS records: `app.` → Cloud Run frontend, `api.` → Cloud Run backend
- [ ] Set Cloudflare SSL to Full (Strict)
- [ ] Configure cache rules for static assets
- [ ] Set up `www` → apex redirect
- [ ] Upload landing page to Cloud Storage bucket for `unstructuredminds.com`
- [ ] Update CORS origins + Clerk allowed origins for production domains

### Week 3 — Product Readiness
- [ ] Implement `user_usage` table + token tracking middleware
- [ ] Add usage display in frontend settings
- [ ] End-to-end testing on production URLs
- [ ] Rotate all credentials, verify secrets
- [ ] Set up Cloud Monitoring alerts (error rate, latency, billing)
- [ ] Privacy policy + ToS (required for Clerk + Stripe)

### Week 4 — Launch
- [ ] Landing page with pricing tiers (all free initially)
- [ ] Set up automated backups (DuckDB cache + vault) to Cloud Storage
- [ ] Soft launch — share with target users
- [ ] Monitor costs + usage

### Post-Launch
- [ ] Stripe integration (Phase 2)
- [ ] Pricing page + checkout flow
- [ ] Usage-based 429 enforcement
- [ ] `--min-instances=1` if cold starts bother users
