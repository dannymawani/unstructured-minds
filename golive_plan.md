# Go-Live Plan — Unstructured Minds

**Domain:** unstructuredminds.com
**Target:** Production-ready SaaS with tiered AI usage

---

## 1. Hosting — Where to Run Docker Compose Cheaply

### Recommendation: **Hetzner Cloud** (CPX21 — 3 vCPU, 4 GB RAM, 80 GB disk)

| Option | Spec | Cost/mo | Pros | Cons |
|--------|------|---------|------|------|
| **Hetzner CPX21** | 3 vCPU / 4 GB / 80 GB | ~$7 | Cheapest for Docker Compose, EU data center, great perf/$ | Less ecosystem than AWS |
| DigitalOcean Droplet | 2 vCPU / 2 GB / 50 GB | ~$12 | Good UI, managed DBs available | Pricier for same spec |
| Railway | Container hosting | ~$5+ usage | Zero DevOps, deploy from GitHub | Less control, unpredictable costs at scale |
| Fly.io | Container hosting | ~$5+ usage | Global edge, easy deploys | Docker Compose not native (needs separate services) |

**Why Hetzner:** You already have a `docker-compose.yml` ready for production. Hetzner lets you `docker compose up -d` on a cheap VPS with zero rearchitecting. A single $7/mo server runs both containers comfortably for early users. When you outgrow it, upgrade the box or split services.

### Setup steps
1. Provision a Hetzner CPX21 (or CPX31 for headroom) running Ubuntu 24.04
2. Install Docker + Docker Compose
3. Clone repo, copy `.env` with production values
4. Run `docker compose up -d`
5. Set up a firewall: allow 80, 443, 22 only
6. Add a swap file (2 GB) as safety net for DuckDB spikes

---

## 2. Domain & DNS — unstructuredminds.com

### Recommendation: **Cloudflare** (free tier) as DNS + CDN + SSL

| Step | Action |
|------|--------|
| **DNS** | Point `unstructuredminds.com` nameservers to Cloudflare |
| **A record** | `@` → Hetzner server IP |
| **CNAME** | `www` → `unstructuredminds.com` |
| **SSL** | Cloudflare "Full (Strict)" mode — free automatic HTTPS |
| **CDN** | Cloudflare proxies all traffic (orange cloud on), caches static assets globally |

### What Cloudflare free tier gives you
- Automatic HTTPS (no certbot needed on server)
- Global CDN for static assets (JS/CSS/images)
- DDoS protection
- Page rules for caching
- Bot management (basic)
- Analytics

### Nginx changes needed
- Update `server_name localhost` → `server_name unstructuredminds.com www.unstructuredminds.com`
- Uncomment the HSTS header
- Update the CSP `connect-src` to include your domain and Clerk domain
- Add redirect from `www` → apex (or vice versa)

---

## 3. AI Token Limits — Tiered Usage

### Architecture

```
User Request → Backend Middleware → Check Quota → Allow/Reject → Claude API
```

### Tier structure (mocked initially, Stripe later)

| Tier | Monthly Token Budget | Extraction | NL Queries | Price |
|------|---------------------|------------|------------|-------|
| **Free** | 100K tokens (~50 extractions) | Haiku only | 10/month | $0 |
| **Pro** | 2M tokens | Haiku + Sonnet | Unlimited | $9/mo |
| **Power** | 10M tokens | All models | Unlimited + priority | $29/mo |

### Implementation phases

**Phase 1 — Soft limits (go-live):**
- Add a `user_usage` table: `user_id`, `month`, `tokens_used`, `request_count`
- Middleware counts tokens from Claude API responses (`usage.input_tokens + usage.output_tokens`)
- Hardcode tier = "free" for all users
- Return `429 Too Many Requests` when budget exceeded
- Show usage bar in the frontend settings page

**Phase 2 — Stripe integration (post-launch):**
- Stripe Checkout for subscription signup
- Webhook handler: `customer.subscription.created/updated/deleted`
- `user_subscriptions` table: `user_id`, `stripe_customer_id`, `tier`, `period_end`
- Middleware reads tier from DB to determine budget
- Stripe Customer Portal for self-service plan changes

### Stripe alternative consideration
Stripe is the standard. Alternatives like Lemon Squeezy (simpler, handles EU VAT) or Polar (built for devtools) are worth considering if you want less setup overhead.

---

## 4. Logo & Brand Identity

### Current state
- No logo exists
- Brand colors are defined (teal `#14b8a6` primary, dark `#0f172a`, etc.)

### Options

| Approach | Cost | Timeline | Quality |
|----------|------|----------|---------|
| **AI-generated + refine** | $0 | 1 day | Good enough for launch |
| Fiverr / 99designs | $50-300 | 3-7 days | Professional |
| Design it yourself (Figma) | $0 | 1-2 days | Depends on skill |

### Minimum for launch
1. **Wordmark + icon** — A simple wordmark "unstructured minds" in the brand font with a small icon (brain/neural-net/node motif in teal)
2. **Favicon** — 32x32 and 16x16 versions of the icon
3. **OG image** — 1200x630 social share card for link previews
4. **Apple touch icon** — 180x180 for iOS bookmarks

### Recommendation
Use an AI tool (Midjourney, DALL-E, or Recraft) to generate a clean icon concept, then refine in Figma. A teal-colored abstract brain/network node mark works well with the existing brand. Don't block launch on a perfect logo — a clean wordmark is enough.

---

## 5. Email — Transactional & Auth

### What you need email for
1. **Auth emails** — Clerk handles these already (verification, password reset, magic links)
2. **Transactional** — Welcome email, usage alerts ("you've hit 80% of your quota"), receipts
3. **Marketing** (later) — Onboarding drip, feature announcements

### Recommendation: **Resend** (free tier: 3,000 emails/month)

| Option | Free tier | Cost after | Pros |
|--------|-----------|------------|------|
| **Resend** | 3K emails/mo | $20/mo for 50K | Modern API, great DX, React Email templates |
| Postmark | 100 emails/mo | $15/mo for 10K | Best deliverability, but tiny free tier |
| SendGrid | 100 emails/day | $20/mo for 50K | Biggest free tier (daily), but complex |
| Clerk built-in | Included | Included | Auth emails only, no custom transactional |

### DNS setup for email (on Cloudflare)
1. Add Resend's DKIM records (3 CNAME records)
2. Add SPF record: `v=spf1 include:resend.com ~all`
3. Add DMARC record: `v=DMARC1; p=quarantine;`
4. Verify domain in Resend dashboard
5. Send from `hello@unstructuredminds.com` or `noreply@unstructuredminds.com`

---

## 6. Production Hardening Checklist

### Secrets management
- [ ] Move all secrets out of `.env` file into environment variables on the server (or use Docker secrets)
- [ ] **Rotate the Anthropic API key** — the current one is in the repo's `.env` file
- [ ] Rotate Supabase credentials if they've been committed to git
- [ ] Add `.env` to `.gitignore` (verify it's there)
- [ ] Never log API keys or tokens

### Security
- [ ] Set `DEBUG=false` in production
- [ ] Remove debug port (5678) exposure
- [ ] Set restrictive CORS origins (only `https://unstructuredminds.com`)
- [ ] Enable Cloudflare "Under Attack" mode toggle (for emergencies)
- [ ] Rate limiting is already in nginx config — verify limits are appropriate

### Monitoring
- [ ] Set up Uptime Kuma (self-hosted, free) or Better Stack free tier for uptime monitoring
- [ ] Configure Docker restart policies (already `unless-stopped`)
- [ ] Set up log rotation for Docker containers
- [ ] Basic alerting: email when server goes down

### Backups
- [ ] DuckDB file: daily cron `cp` to a backup directory + weekly push to S3/Supabase storage
- [ ] Vault markdown files: same backup strategy
- [ ] Supabase Postgres: automatic backups included in Supabase

---

## 7. Go-Live Sequence

### Week 1 — Infrastructure
- [ ] Provision Hetzner VPS
- [ ] Set up Cloudflare DNS for unstructuredminds.com
- [ ] Deploy Docker Compose to server
- [ ] Verify HTTPS works end-to-end
- [ ] Rotate all leaked credentials

### Week 2 — Product Readiness
- [ ] Create logo (even if temporary wordmark)
- [ ] Add favicon and OG meta tags
- [ ] Implement token usage tracking (Phase 1 soft limits)
- [ ] Add a simple landing page / marketing page explaining the product
- [ ] Set up Resend for transactional email

### Week 3 — Polish & Launch
- [ ] End-to-end testing on production server
- [ ] Set up uptime monitoring
- [ ] Set up automated backups
- [ ] Write a minimal privacy policy and terms of service (required for Clerk + Stripe)
- [ ] Soft launch: share with friends / target users

### Post-Launch
- [ ] Stripe integration for paid tiers
- [ ] Usage dashboard in frontend
- [ ] Marketing email drip via Resend
- [ ] Analytics (Plausible self-hosted or Cloudflare Web Analytics — both privacy-friendly)

---

## Cost Summary (at launch)

| Item | Monthly Cost |
|------|-------------|
| Hetzner CPX21 | $7 |
| Cloudflare | $0 (free tier) |
| Domain renewal | ~$1 (amortized) |
| Resend | $0 (free tier) |
| Clerk | $0 (free tier up to 10K MAU) |
| Supabase | $0 (free tier) or $25 (Pro) |
| Anthropic API | Variable (pass-through to users via tiers) |
| **Total fixed** | **~$8-33/mo** |

The Anthropic API cost is the only variable. With token budgets per user and tiered pricing, Pro/Power subscriptions should cover API costs and generate margin.
