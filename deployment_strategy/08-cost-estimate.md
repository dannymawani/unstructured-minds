# 08 - Cost Estimate

## Fixed Monthly Costs (Before Any Users)

| Service | Tier | Cost | What You Get |
|---------|------|------|-------------|
| Vercel | Free | $0 | 100K page views, custom domain, SSL |
| Railway | Hobby | $5 | 512MB RAM, 1 vCPU, 1GB disk, custom domain |
| Supabase | Free | $0 | 500MB Postgres, 50K MAU auth, 1GB bandwidth |
| Cloudflare R2 | Free | $0 | 10GB storage, 10M reads, 1M writes/month |
| Upstash Redis | Free | $0 | 10K commands/day, 256MB |
| Clerk | Free | $0 | 10K MAU, Google OAuth, webhooks |
| Domain | Annual | ~$1/mo | unstructuredminds.com |
| **Total** | | **~$6/mo** | |

That's it. $6/month to run the entire platform for the first ~100 users.

## Variable Costs (Per User)

### Anthropic API (The Big One)

| User Type | Monthly API Cost to Us |
|-----------|----------------------|
| Free tier (50 ops) | ~$1.50 |
| BYO key user | $0.00 |
| Pro tier (500 ops) | ~$5-8 (they pay $12) |

### Storage (Per User)

| Resource | Average Size | Cost/User/Month |
|----------|-------------|-----------------|
| DuckDB file on R2 | 10-100 MB | $0.0015 (negligible) |
| Google Drive | N/A | $0 (user's storage) |
| Supabase row | ~1 KB | $0 (within free tier) |
| Redis cache | ~5 MB | $0 (within free tier) |

## Scaling Scenarios

### 10 Users (Friends & Beta)

```
Fixed costs:           $6
Free tier API (8):     $12
BYO key (2):           $0
────────────────────────
Total:                 $18/month
Revenue:               $0
Net:                   -$18/month
```

### 100 Users (Early Traction)

```
Fixed costs:           $6
Free tier API (70):    $105
BYO key (20):          $0
Pro tier API (10):     $60
────────────────────────
Total costs:           $171/month
Pro revenue (10):      $120/month
Net:                   -$51/month
```

### 500 Users (Growing)

| | Count | API Cost | Revenue |
|---|---|---|---|
| Free | 350 | $525 | $0 |
| BYO Key | 100 | $0 | $0 |
| Pro | 50 | $300 | $600 |
| **Total** | **500** | **$825** | **$600** |

```
Fixed costs:           $25 (upgrade Railway to Pro)
Variable API costs:    $825
────────────────────────
Total costs:           $850/month
Revenue:               $600/month
Net:                   -$250/month
```

Need ~15% Pro conversion to break even. Achievable with good product.

### 2,000 Users (Product-Market Fit)

| | Count | API Cost | Revenue |
|---|---|---|---|
| Free | 1200 | $1,800 | $0 |
| BYO Key | 500 | $0 | $0 |
| Pro | 300 | $1,800 | $3,600 |
| **Total** | **2000** | **$3,600** | **$3,600** |

```
Fixed costs:           $100 (Railway Team, Supabase Pro, Vercel Pro)
Variable API costs:    $3,600
────────────────────────
Total costs:           $3,700/month
Revenue:               $3,600/month
Net:                   -$100/month (roughly break-even)
```

### 10,000 Users (Serious Business)

| | Count | API Cost | Revenue |
|---|---|---|---|
| Free | 5000 | $7,500 | $0 |
| BYO Key | 3000 | $0 | $0 |
| Pro | 2000 | $12,000 | $24,000 |
| **Total** | **10000** | **$19,500** | **$24,000** |

```
Fixed costs:           $500
Variable API costs:    $19,500
────────────────────────
Total costs:           $20,000/month
Revenue:               $24,000/month
Net:                   +$4,000/month
```

## Cost Reduction Levers

### 1. Prompt Caching (-50% on extraction)
Anthropic prompt caching saves ~90% on cached system prompt tokens. Since extraction uses the same system prompt every time, this cuts extraction costs roughly in half.

### 2. Batch API (-50% on bulk operations)
New user onboarding can batch-extract all imported notes at 50% discount.

### 3. Model Selection
Use Haiku 4.5 for everything possible. Only use Sonnet when reasoning quality matters (queries, insights).

### 4. Reduce Free Tier
If costs are too high, reduce free tier from 50 to 25 operations. Or make extraction free (Haiku is cheap) and only count Sonnet queries.

### 5. Aggressive Caching
Cache query results. If 10 users ask "How did I sleep this week?", the SQL pattern is the same - only the data differs. Cache the generated SQL per schema pattern.

## When to Upgrade Services

| Trigger | Action | New Cost |
|---------|--------|----------|
| >100 MAU or need more features | Railway Pro ($20/mo) | +$15 |
| >500 MB Postgres | Supabase Pro ($25/mo) | +$25 |
| >100K page views | Vercel Pro ($20/mo) | +$20 |
| >10K MAU auth | Clerk Pro ($25/mo) | +$25 |
| >10K Redis commands/day | Upstash Pro ($10/mo) | +$10 |
| >10GB R2 storage | R2 paid (pay per GB) | ~$5 |

## One-Time Costs

| Item | Cost | When |
|------|------|------|
| Domain registration | ~$12/year | Phase 0 |
| Google OAuth verification | $0 (if <100 users) or $75 (security audit) | Phase 1 |
| App Store listing (future) | $99/year (Apple) | Phase 5 |
| Legal (Privacy Policy) | $0-500 (template vs lawyer) | Phase 3 |

## Summary

| Phase | Monthly Cost | Revenue |
|-------|-------------|---------|
| Development (you only) | $6 | $0 |
| Beta (10 users) | $18 | $0 |
| Launch (100 users) | $171 | $120 |
| Growth (500 users) | $850 | $600 |
| PMF (2000 users) | $3,700 | $3,600 |
| Scale (10000 users) | $20,000 | $24,000 |

**Bottom line**: You can launch and run this for ~$6/month until you have real users. The free tiers of Vercel, Supabase, Clerk, R2, and Upstash are incredibly generous. The only meaningful cost is the Anthropic API, and that scales linearly with users.
