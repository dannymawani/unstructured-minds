---
name: infra-review
description: Review infrastructure components for security flaws and cost-heavy issues. Covers Docker, Terraform/Azure, nginx, CI/CD, auth, secrets, and cloud cost optimization. Use when assessing infrastructure changes or running a full security/cost audit.
---

# Infrastructure Security & Cost Review

Review all infrastructure components in the Unstructured Minds project for security vulnerabilities and cost risks.

## What to Review

### Files to Read

```
# Terraform / Azure
azure_infrastructure/*.tf
azure_infrastructure/.gitignore
azure_infrastructure/terraform.tfvars.example

# Docker
backend/Dockerfile
frontend/Dockerfile
frontend/Dockerfile.dev (if exists)
docker-compose.yml
docker-compose.dev.yml

# Nginx & Security Headers
frontend/nginx.conf
frontend/nginx/security-headers.conf

# Backend Security
backend/src/middleware/__init__.py
backend/src/middleware/security_headers.py
backend/src/middleware/clerk_auth.py
backend/src/middleware/rate_limit.py
backend/src/middleware/validation.py
backend/src/middleware/request_logging.py
backend/src/api/dependencies.py
backend/src/main.py
backend/src/config.py

# CI/CD
.github/workflows/*.yml

# Secrets / Environment
.gitignore
.env.example (if exists)

# Migration Plan
docs/azure_migration_plan.md
```

## Security Checklist

### Terraform / Azure

- [ ] **State backend encrypted**: Azure Storage with access policies, no public access
- [ ] **Provider versions pinned**: `~>` is acceptable, exact pins for production
- [ ] **Postgres firewall**: NOT using `0.0.0.0/0.0.0.0` (allows all Azure tenants). Use VNet rules or specific IPs
- [ ] **Postgres SSL enforced**: `require_secure_transport = true` in server parameters
- [ ] **Postgres backup configured**: `backup_retention_days` set (7-35 days)
- [ ] **Postgres authentication**: Entra ID auth preferred over password-only
- [ ] **ACR admin disabled**: `admin_enabled = false`, use service principal RBAC
- [ ] **ACR image retention**: Retention policy to auto-delete old untagged images
- [ ] **Container Apps secrets**: All sensitive values use `secret_name` references, never plain `value`
- [ ] **Container Apps ingress**: TLS enforced, HTTP-to-HTTPS redirect
- [ ] **Entra OIDC scope**: Federated identity limited to specific repo+branch
- [ ] **Role assignments**: Least privilege — avoid `Contributor` when `AcrPush` + specific roles suffice
- [ ] **Resource locks**: Production resource group has `CanNotDelete` lock
- [ ] **Tags consistent**: All resources tagged with project, managed_by, tier
- [ ] **No secrets in outputs**: Sensitive outputs marked `sensitive = true`

### Docker

- [ ] **Non-root user in production**: Dockerfile creates and switches to non-root user
- [ ] **Multi-stage build**: No build tools, source, or secrets in final image
- [ ] **Pinned base images**: Use specific tags (`python:3.13-slim`), not `latest`
- [ ] **No secrets in build args**: Build args don't contain sensitive values (VITE_CLERK_PUBLISHABLE_KEY is public, so it's fine)
- [ ] **Health checks defined**: Both Dockerfile and compose have health checks
- [ ] **Dev-only ports not in prod compose**: Debug ports (5678) only in dev override
- [ ] **Production compose doesn't run as root**: No `user: "0:0"` in docker-compose.yml
- [ ] **Volumes use least privilege**: `:ro` where possible, `:rw` only where needed

### Nginx

- [ ] **HSTS enabled**: `Strict-Transport-Security` header uncommented when TLS is configured
- [ ] **CSP strict**: No `unsafe-inline` or `unsafe-eval` in script-src (use nonces/hashes instead)
- [ ] **X-Frame-Options**: Set to `DENY` or `SAMEORIGIN`
- [ ] **X-Content-Type-Options**: `nosniff`
- [ ] **Referrer-Policy**: `strict-origin-when-cross-origin` or stricter
- [ ] **Permissions-Policy**: Restricts unnecessary browser APIs
- [ ] **Server tokens off**: `server_tokens off` prevents nginx version disclosure
- [ ] **Rate limiting**: API and general rate limits configured with appropriate burst
- [ ] **Sensitive paths blocked**: `.env`, `.git`, backup files denied
- [ ] **Proxy headers**: `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` set
- [ ] **Timeout values reasonable**: Not too long (DoS risk) or too short (breaks Claude API calls)

### Backend Security

- [ ] **Auth on all endpoints**: Cloud mode requires JWT on every non-health endpoint
- [ ] **JWT verification**: Clerk token verified with JWKS, not just decoded
- [ ] **User isolation**: All database queries scoped to authenticated user_id
- [ ] **CORS origins explicit**: No wildcard `*`, only specific domains
- [ ] **Rate limiting applied**: slowapi configured with appropriate limits
- [ ] **Input validation**: File paths, query lengths, file sizes validated
- [ ] **Error responses sanitized**: No stack traces, internal paths, or secrets in error responses
- [ ] **Request logging safe**: No authorization headers, tokens, or PII in logs
- [ ] **SQL injection prevented**: Parameterized queries, no string interpolation

### CI/CD

- [ ] **OIDC auth**: Using federated identity, not long-lived secrets
- [ ] **Minimal permissions**: `id-token: write` + `contents: read` only
- [ ] **Branch protection**: Federated identity scoped to `refs/heads/main`
- [ ] **No secrets in logs**: Build commands don't echo sensitive values
- [ ] **Dependency pinning**: `npm ci` (not `npm install`), pinned action versions

### Secrets Management

- [ ] **`.env` gitignored**: Root `.env` file in `.gitignore`
- [ ] **`terraform.tfvars` gitignored**: In `azure_infrastructure/.gitignore`
- [ ] **No secrets in code**: Grep for patterns like `sk_live`, `sk-ant-`, `password =`, API keys
- [ ] **Sensitive Terraform outputs**: Marked with `sensitive = true`
- [ ] **Example files safe**: `.env.example` and `terraform.tfvars.example` have placeholder values only

## Cost Checklist

### Free Tier Tracking

| Resource | Free Period | Post-Free Cost | Action |
|----------|------------|----------------|--------|
| PostgreSQL Flexible Server B1ms | 12 months | ~$15/mo | Set calendar reminder at month 11; evaluate Neon/Supabase fallback |
| Container Registry Basic | 12 months | ~$5/mo | Evaluate if still needed or switch to GitHub Container Registry (free) |
| Container Apps Consumption | Always free (180K vCPU-sec/mo) | Overage: ~$0.000012/vCPU-sec | Monitor usage, keep max_replicas low |
| Static Web Apps Free | Always free | N/A | No action needed |
| Terraform state storage | ~$0.02/GB/mo | Same | Negligible |

### Cost Controls

- [ ] **Azure budget alert**: Create budget with alert at 80% and 100% thresholds
- [ ] **Container Apps max_replicas**: Set to minimum needed (2 is fine for 10 users)
- [ ] **Container Apps min_replicas=0**: Scale to zero when idle (saves vCPU-seconds)
- [ ] **ACR retention policy**: Auto-delete untagged images older than 7 days
- [ ] **Claude API per-user limits**: Backend enforces daily/monthly token limits per user
- [ ] **No auto-scaling surprises**: Review scaling rules, set hard maximums
- [ ] **Resource tagging**: All resources tagged with `tier` (free, free-12mo, paid) for cost visibility
- [ ] **Monthly cost review**: Check Azure Cost Management dashboard monthly

### Cost Red Flags to Grep For

```bash
# Uncapped scaling
grep -r "max_replicas" azure_infrastructure/  # Should be low (1-3)

# Missing retention
grep -r "retention" azure_infrastructure/     # Should exist for ACR, Postgres backup

# Premium SKUs
grep -r "sku" azure_infrastructure/           # Verify all are free/basic tier

# Large storage
grep -r "storage_mb" azure_infrastructure/    # Should be 32768 (free tier max)
```

## How to Run This Review

1. Read all files listed above
2. Walk through each checklist item
3. For each failing check, note:
   - **File and line number**
   - **What's wrong**
   - **Security or cost impact**
   - **Recommended fix** (with code snippet)
4. Summarize with counts: X critical, Y high, Z medium, W cost risks
5. List what's done well (positive reinforcement motivates continued good practices)

## Known Accepted Risks

Document any risks that have been consciously accepted:

- Dev compose running as root (convenience for bind mounts, dev-only)
- Debug port 5678 exposed (dev-only, not in production compose)
- CSP `unsafe-inline` may be required for Clerk SDK (verify and document)
- No VNet integration (not available on free tier Postgres)
