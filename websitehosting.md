# Website Hosting Plan — unstructuredminds.com

**Domain registrar:** GoDaddy
**DNS / CDN / SSL:** Cloudflare (free tier)
**Landing page hosting:** Cloudflare Pages
**Application hosting:** GCP Cloud Run (future — see `golive_plan.md`)

---

## Current State

### Completed (Feb 18, 2026)

- [x] Domain `unstructuredminds.com` registered on GoDaddy
- [x] Nameservers changed from GoDaddy to Cloudflare (`clara.ns.cloudflare.com`, `dax.ns.cloudflare.com`)
- [x] DNS cleanup — removed unauthorized Mailgun records (MX, SPF, DKIM, DMARC, email CNAME)
- [x] Cloudflare Pages project created (`unstructured-minds-landing`)
- [x] GitHub Actions secrets set (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`)
- [x] Coming soon landing page deployed and live at `unstructuredminds.com`
- [x] Custom domain configured in Cloudflare Pages

### DNS cleanup needed (working with GoDaddy support)

Records to **delete** (not set up by us, likely GoDaddy defaults or unauthorized):

| Record | Type | Content | Action |
|--------|------|---------|--------|
| `unstructuredminds.com` | A | 13.248.243.5 | Delete (GoDaddy parking) |
| `unstructuredminds.com` | A | 76.223.105.230 | Delete (GoDaddy parking) |
| `email` | CNAME | mailgun.org | Delete (not ours) |
| `unstructuredminds.com` | MX | mxb.mailgun... | Delete (not ours) |
| `unstructuredminds.com` | MX | mxa.mailgun... | Delete (not ours) |
| `mx._domainkey` | TXT | DKIM key | Delete (not ours) |
| `unstructuredminds.com` | TXT | SPF record | Delete (not ours) |
| `_dmarc` | TXT | DMARC policy | Delete (not ours) |

Records to **keep**:

| Record | Type | Content | Notes |
|--------|------|---------|-------|
| `_domainconnect` | CNAME | GoDaddy default | Standard, harmless |
| `www` | CNAME | unstructuredminds.com | Keep, will use |

### Security checklist

- [ ] Change GoDaddy password
- [ ] Enable 2FA on GoDaddy
- [ ] Review GoDaddy account login history
- [ ] Change Cloudflare password
- [ ] Enable 2FA on Cloudflare
- [ ] Review Cloudflare audit log (Manage Account > Audit Log)
- [ ] Confirm all unauthorized records are deleted

---

## Phase 1 — Coming Soon Landing Page

Deploy the landing page to Cloudflare Pages and point the domain to it.

### Step 1: Cloudflare Pages project setup

1. Go to Cloudflare dashboard > Pages
2. Create project: **unstructured-minds-landing**
3. Choose "Direct Upload" or connect GitHub repo
4. Set build output directory: `landing/`

### Step 2: GitHub Actions deployment (automated)

The workflow at `.github/workflows/deploy-landing.yml` auto-deploys on push to `main` when `landing/**` files change.

**Required GitHub secrets:**

| Secret | Where to find it |
|--------|-----------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare > My Profile > API Tokens > Create Token (Cloudflare Pages: Edit) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard URL: `dash.cloudflare.com/<account-id>` |

### Step 3: DNS records for landing page

After cleanup, the DNS should look like this:

| Record | Type | Content | Proxy | Notes |
|--------|------|---------|-------|-------|
| `unstructuredminds.com` | CNAME | `unstructured-minds-landing.pages.dev` | Proxied | Root domain → Cloudflare Pages |
| `www` | CNAME | `unstructuredminds.com` | Proxied | www redirect to apex |

**Note:** Cloudflare allows CNAME flattening on the root domain (unlike most DNS providers), so a CNAME on `unstructuredminds.com` works.

**Alternative:** Use the Cloudflare Pages custom domain feature:
1. Go to Pages project > Custom domains
2. Add `unstructuredminds.com`
3. Cloudflare auto-creates the DNS record

### Step 4: Cloudflare settings

| Setting | Value | Where |
|---------|-------|-------|
| SSL/TLS mode | **Full (Strict)** | SSL/TLS > Overview |
| Always Use HTTPS | On | SSL/TLS > Edge Certificates |
| Automatic HTTPS Rewrites | On | SSL/TLS > Edge Certificates |
| Minimum TLS Version | 1.2 | SSL/TLS > Edge Certificates |
| Browser Cache TTL | 4 hours | Caching > Configuration |
| Auto Minify | JS + CSS + HTML | Speed > Optimization |

### Step 5: Redirect rules

| Rule | What |
|------|------|
| `www.unstructuredminds.com/*` → `https://unstructuredminds.com/$1` | www to apex 301 redirect |

Set up in: Rules > Redirect Rules (or Page Rules on free tier)

---

## Phase 2 — Application Deployment

When ready to deploy the full app (see `golive_plan.md` for details):

### DNS records to add

| Record | Type | Content | Proxy |
|--------|------|---------|-------|
| `app.unstructuredminds.com` | CNAME | `um-frontend-xxx.europe-north1.run.app` | Proxied |
| `api.unstructuredminds.com` | CNAME | `um-backend-xxx.europe-north1.run.app` | Proxied |

### Email setup (when needed)

When we need transactional email (e.g., for notifications), set up properly with a service we control:

| Record | Type | Content | Proxy |
|--------|------|---------|-------|
| `unstructuredminds.com` | MX | Provider MX servers | DNS only |
| `unstructuredminds.com` | TXT | `v=spf1 include:<provider> -all` | DNS only |
| `<selector>._domainkey` | TXT | DKIM public key | DNS only |
| `_dmarc` | TXT | `v=DMARC1; p=reject; rua=mailto:...` | DNS only |

Use `p=reject` (not `p=none`) to prevent others from spoofing our domain.

---

## Quick Reference

### Cloudflare free tier includes

- Global CDN (300+ edge locations)
- Unlimited DNS queries
- Free SSL certificates (auto-renewed)
- DDoS protection (unlimited, unmetered)
- 5 page rules
- Cloudflare Pages (unlimited sites, 500 builds/month)
- Web Analytics (privacy-friendly)

### Accounts needed

| Service | URL | Purpose |
|---------|-----|---------|
| GoDaddy | godaddy.com | Domain registrar only |
| Cloudflare | dash.cloudflare.com | DNS, CDN, SSL, Pages hosting |
| GitHub | github.com | Code + CI/CD via Actions |
| GCP | console.cloud.google.com | App hosting (Phase 2) |
