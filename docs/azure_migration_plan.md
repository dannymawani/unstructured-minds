# Azure Migration Plan

Migrate Unstructured Minds from local Docker Compose + Neon Postgres to Azure free tier infrastructure with production Clerk, Stripe billing, and Terraform IaC.

**Principles:**
- **Terraform-first** — every Azure resource is defined in Terraform and created via `terraform apply`. No manual resource creation, no importing after the fact.
- **Free tier only** — all Azure resources use always-free or 12-month free tiers. Zero Azure spend in year 1 (external costs: Claude API only).

## Current State

| Component | Current | Notes |
|-----------|---------|-------|
| Frontend | Docker (nginx:alpine) | Served locally on port 3000 |
| Backend | Docker (python:3.13-slim) | FastAPI on port 8000 |
| Database | Neon Postgres (Azure region) | `ep-gentle-lake-a91pv4xj-pooler.gwc.azure.neon.tech` |
| Auth | Clerk test instance | `more-cobra-67.clerk.accounts.dev` |
| Billing | None | Free single-user |
| CI/CD | Landing page only | Cloudflare Pages via GitHub Actions |
| IaC | None | Manual setup |

## Target State

| Component | Azure Service | Tier | Cost |
|-----------|--------------|------|------|
| Frontend | Static Web Apps | Free (always) | $0 |
| Backend | Container Apps | Consumption (always free) | $0 |
| Database | PostgreSQL Flexible Server | B1ms (free 12 months) | $0 → ~$15/mo |
| Registry | Container Registry | Basic (free 12 months) | $0 → ~$5/mo |
| Auth | Clerk production instance | Free tier (10K MAU) | $0 |
| Billing | Stripe | Standard | 2.9% + $0.30/txn |
| DNS | Azure DNS or Cloudflare | Free tier | $0 |
| IaC | Terraform | N/A | $0 |
| CI/CD | GitHub Actions | Free tier (2K min/mo) | $0 |
| AI | Claude API (Anthropic) | External | ~$20-30/mo for 10 users |

**Year 1 total: ~$20-30/month (Claude API only)**
**After year 1: ~$40-50/month (+ Postgres + Registry)**

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │                   Azure                      │
                    │                                              │
  Users ──HTTPS──▶  │  Static Web Apps ──/api/──▶ Container Apps  │
                    │  (React SPA)                (FastAPI + DuckDB)│
                    │                                    │         │
                    │                                    ▼         │
                    │                          PostgreSQL Flexible  │
                    │                            Server (B1ms)     │
                    │                                              │
                    │  Container Registry ◀── GitHub Actions CI/CD │
                    │                                              │
                    └─────────────────────────────────────────────┘
                                         │
                              ┌──────────┼──────────┐
                              ▼          ▼          ▼
                          Clerk      Anthropic    Stripe
                         (Auth)     (Claude AI)  (Billing)
```

---

## Phase 0: Prerequisites + Terraform Foundation

**Goal:** Azure account, tooling, Terraform state backend, and Entra OIDC for CI/CD. All subsequent phases create resources via `terraform apply`.

- [ ] Create Azure account (new account = 12-month free tier + $200 credit)
- [ ] Install Azure CLI (`az`), Terraform, and `gh` CLI
- [ ] `az login` and set default subscription
- [ ] Bootstrap Terraform state storage (the only manual step — chicken-and-egg):
  ```bash
  az group create --name rg-terraform-state --location germanywestcentral
  az storage account create --name umtfstate --resource-group rg-terraform-state \
    --location germanywestcentral --sku Standard_LRS
  az storage container create --name tfstate --account-name umtfstate
  ```
- [ ] Write initial Terraform files (main.tf, variables.tf, resource_group.tf, entra.tf)
- [ ] `terraform init && terraform apply` — creates resource group + Entra OIDC
- [ ] Configure GitHub secrets with Entra OIDC credentials

### 0.1 Terraform state backend

```hcl
# azure_infrastructure/main.tf
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "umtfstate"
    container_name       = "tfstate"
    key                  = "unstructured-minds.tfstate"
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

provider "azuread" {}
```

### 0.2 Entra OIDC for GitHub Actions

```hcl
# azure_infrastructure/entra.tf
resource "azuread_application" "github_actions" {
  display_name = "um-github-actions"
}

resource "azuread_service_principal" "github_actions" {
  client_id = azuread_application.github_actions.client_id
}

resource "azuread_application_federated_identity_credential" "github" {
  application_id = azuread_application.github_actions.id
  display_name   = "github-main"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:dmh/unstructured-minds:ref:refs/heads/main"
}

# Grant Contributor on the resource group
resource "azurerm_role_assignment" "github_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github_actions.object_id
}
```

**Terraform folder structure:**
```
azure_infrastructure/
  main.tf              # Provider config, backend state
  variables.tf         # Input variables
  outputs.tf           # Connection strings, URLs
  resource_group.tf    # Resource group
  entra.tf             # Entra app registration + OIDC
  postgres.tf          # PostgreSQL Flexible Server (free 12mo)
  container_apps.tf    # Container Apps environment + app (free)
  static_web_app.tf    # Static Web Apps (always free)
  registry.tf          # Container Registry (free 12mo)
  dns.tf               # DNS zones (optional, can use Cloudflare)
  terraform.tfvars     # Non-secret values (gitignored)
```

Each subsequent phase adds a `.tf` file and runs `terraform apply` to provision.

**Estimated effort:** 2-3 hours

---

## Phase 1: Azure PostgreSQL

**Goal:** Replace Neon Postgres with Azure PostgreSQL Flexible Server. Add `postgres.tf` and `terraform apply`.

### 1.1 Provision

```hcl
# azure_infrastructure/postgres.tf
resource "azurerm_postgresql_flexible_server" "main" {
  name                = "um-postgres"
  resource_group_name = azurerm_resource_group.main.name
  location            = "germanywestcentral"   # Same region as current Neon
  sku_name            = "B_Standard_B1ms"       # Free tier eligible
  storage_mb          = 32768                   # 32 GB (free tier max)
  version             = "16"

  authentication {
    password_auth_enabled = true
  }

  administrator_login    = "umadmin"
  administrator_password = var.postgres_password
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "unstructured_minds"
  server_id = azurerm_postgresql_flexible_server.main.id
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name      = "AllowAzureServices"
  server_id = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
```

### 1.2 Migrate data

```bash
# Export from Neon
pg_dump --no-owner --no-acl \
  "postgresql://neondb_owner:***@ep-gentle-lake-a91pv4xj-pooler.gwc.azure.neon.tech/neondb?sslmode=require" \
  > backup.sql

# Import to Azure PostgreSQL
psql "postgresql://umadmin:***@um-postgres.postgres.database.azure.com/unstructured_minds?sslmode=require" \
  < backup.sql
```

### 1.3 Update connection

```env
# New DATABASE_URL (Azure PostgreSQL)
DATABASE_URL=postgresql://umadmin:${POSTGRES_PASSWORD}@um-postgres.postgres.database.azure.com/unstructured_minds?sslmode=require
```

**No code changes needed** — the app uses psycopg3 with `prepare_threshold=None`, which works with Azure PostgreSQL natively (no PgBouncer compatibility issues since Azure uses built-in connection management).

### 1.4 Keep Neon as backup

Don't delete Neon immediately. Keep the `SUPABASE_DATABASE_URL` / Neon URL in `.env` as a rollback target for 30 days.

**Estimated effort:** 2-3 hours

---

## Phase 2: Container Registry + Backend Deployment

**Goal:** Deploy the FastAPI backend to Azure Container Apps. Add `registry.tf` + `container_apps.tf` and `terraform apply`.

### 2.1 Container Registry

```hcl
# azure_infrastructure/registry.tf
resource "azurerm_container_registry" "main" {
  name                = "umcontainerreg"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"           # Free for 12 months
  admin_enabled       = true
}
```

### 2.2 Container Apps Environment

```hcl
# azure_infrastructure/container_apps.tf
resource "azurerm_container_app_environment" "main" {
  name                = "um-env"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

resource "azurerm_container_app" "backend" {
  name                         = "um-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    min_replicas = 0    # Scale to zero when idle
    max_replicas = 2

    container {
      name   = "backend"
      image  = "${azurerm_container_registry.main.login_server}/um-backend:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "ANTHROPIC_API_KEY"
        secret_name = "anthropic-api-key"
      }
      env {
        name        = "CLERK_SECRET_KEY"
        secret_name = "clerk-secret-key"
      }
      env {
        name  = "CLERK_DOMAIN"
        value = var.clerk_domain
      }
      env {
        name  = "USE_CLOUD"
        value = "true"
      }
      env {
        name  = "CORS_ORIGINS"
        value = "https://app.unstructuredminds.com"
      }

      liveness_probe {
        path      = "/health/live"
        port      = 8000
        transport = "HTTP"
      }

      readiness_probe {
        path      = "/health/ready"
        port      = 8000
        transport = "HTTP"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  secret {
    name  = "database-url"
    value = var.database_url
  }
  secret {
    name  = "anthropic-api-key"
    value = var.anthropic_api_key
  }
  secret {
    name  = "clerk-secret-key"
    value = var.clerk_secret_key
  }
}
```

### 2.3 Backend code changes

**Cold start optimization** — Container Apps scales to zero. Add to `backend/src/main.py`:
```python
# The existing health checks (/health/live, /health/ready) already handle this.
# DuckDB analytics cache rebuilds on first request per user — no change needed.
# Postgres pool opens lazily — no change needed.
```

No backend code changes required. The existing health probes and lazy initialization handle scale-to-zero gracefully.

### 2.4 Build and push

```bash
# Initial manual push (CI/CD automates this later)
az acr login --name umcontainerreg
docker build -t umcontainerreg.azurecr.io/um-backend:latest ./backend
docker push umcontainerreg.azurecr.io/um-backend:latest
```

**Estimated effort:** 3-4 hours

---

## Phase 3: Frontend Deployment

**Goal:** Deploy React SPA to Azure Static Web Apps. Add `static_web_app.tf` and `terraform apply`.

### 3.1 Provision

```hcl
# azure_infrastructure/static_web_app.tf
resource "azurerm_static_web_app" "frontend" {
  name                = "um-frontend"
  resource_group_name = azurerm_resource_group.main.name
  location            = "westeurope"
  sku_tier            = "Free"
  sku_size            = "Free"
}
```

### 3.2 Static Web Apps config

Create `frontend/staticwebapp.config.json`:
```json
{
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/assets/*", "/*.svg", "/*.ico"]
  },
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["anonymous"]
    }
  ],
  "globalHeaders": {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin"
  },
  "mimeTypes": {
    ".json": "application/json",
    ".woff2": "font/woff2"
  }
}
```

### 3.3 API proxy vs direct calls

Two options:

**Option A: Direct API calls (recommended for simplicity)**
- Frontend calls `https://um-backend.<region>.azurecontainerapps.io/api/...` directly
- Set `VITE_API_URL` at build time
- CORS on backend allows the Static Web App domain

**Option B: Azure Static Web Apps linked backend**
- Static Web Apps can proxy `/api/*` to a linked Container App
- More complex to configure, but cleaner URLs

Start with Option A. Migrate to B later if desired.

### 3.4 Frontend code changes

Update the CORS_ORIGINS env to include the Static Web App URL. No frontend code changes — `VITE_API_URL` is already configurable at build time.

**Estimated effort:** 1-2 hours

---

## Phase 4: Clerk Production

**Goal:** Switch from Clerk test instance to production.

### 4.1 Clerk dashboard

1. Go to [clerk.com/dashboard](https://clerk.com/dashboard)
2. Create a **production instance** (or promote the existing one)
3. Configure custom domain: `auth.unstructuredminds.com` (optional, adds branding)
4. Set allowed redirect URLs: `https://app.unstructuredminds.com`
5. Configure social logins (Google, GitHub) if desired
6. Note new keys:
   - `CLERK_SECRET_KEY` (starts with `sk_live_`)
   - `VITE_CLERK_PUBLISHABLE_KEY` (starts with `pk_live_`)
   - `CLERK_DOMAIN` (your production domain)

### 4.1.1 Invitation-only signup

Restrict account creation so only people you explicitly invite can sign up.

1. In Clerk Dashboard → **User & Authentication → Restrictions**
2. Enable **"Restrict sign-ups"**
3. Set sign-up mode to **"Invitation only"**

This disables public registration entirely. To invite users:

1. Go to Clerk Dashboard → **Users → Invitations**
2. Click **"Invite user"**, enter their email address
3. Clerk sends them a signup link — only that link allows account creation

**How it works:**
- Existing users sign in normally (the `<SignInButton>` modal works as-is)
- Invited users click the email link → Clerk signup flow with pre-filled email
- Anyone else attempting to sign up is blocked by Clerk
- No frontend code changes needed — `SignInGate` already shows only "Sign In"

**Note:** The free Clerk tier (10K MAU) includes unlimited invitations. You can also revoke pending invitations from the dashboard.

### 4.2 User migration

Clerk test instances have separate user databases. Options:

**Option A: Fresh start (recommended for <10 users)**
- Users re-sign-up on production
- Run data migration script to remap `user_id` UUIDs:

```python
# scripts/remap_user_ids.py
"""Remap user IDs after Clerk production migration."""
import uuid

OLD_USER_ID = "4e866c49-1e83-5366-b93f-3f92b14803b4"  # Current test UUID
NEW_CLERK_SUB = "user_xxx"  # New production Clerk sub claim
NEW_USER_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, NEW_CLERK_SUB))

TABLES = [
    "daily_metrics", "exercise_log", "activities", "food_log",
    "tasks", "vault_files", "user_settings", "extraction_log",
    "kanban_tasks", "kanban_task_updates", "progress_reviews",
    "custom_extractions", "file_index", "community_exercises",
]

# UPDATE {table} SET user_id = '{NEW_USER_ID}' WHERE user_id = '{OLD_USER_ID}';
```

**Option B: Clerk user export/import**
- Export users from test instance via Clerk API
- Import to production instance
- User IDs (`sub` claims) stay the same, so no DB remapping needed
- Only works if Clerk preserves the `user_xxx` format across instances

### 4.3 Update environment

```env
# Container Apps secrets
CLERK_SECRET_KEY=sk_live_...
CLERK_DOMAIN=clerk.unstructuredminds.com  # or default Clerk domain

# Frontend build arg
VITE_CLERK_PUBLISHABLE_KEY=pk_live_...
```

### 4.4 Update CSP

Update `frontend/nginx/security-headers.conf` (or `staticwebapp.config.json` if using Static Web Apps) to allow the new Clerk production domain instead of `*.clerk.accounts.dev`.

**Estimated effort:** 2-3 hours

---

## Phase 6: Stripe Integration (When Ready)

**Goal:** Add subscription billing for users beyond free tier. Deferred until you're ready to charge.

### 6.1 Stripe setup

1. Create Stripe account at [stripe.com](https://stripe.com)
2. Create products/prices:
   - **Free**: 0/mo — 1 user, basic features
   - **Pro**: $X/mo — unlimited notes, full dashboard, chat queries
3. Set up webhook endpoint: `https://um-backend.<region>.azurecontainerapps.io/api/billing/webhook`
4. Note: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`

### 6.2 Backend changes

```
backend/
  src/
    api/
      billing.py          # NEW: Stripe webhook handler, checkout, portal
    middleware/
      subscription.py     # NEW: Check active subscription on protected routes
```

**New endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/billing/checkout` | Create Stripe Checkout session |
| POST | `/api/billing/webhook` | Stripe webhook receiver |
| GET | `/api/billing/portal` | Redirect to Stripe Customer Portal |
| GET | `/api/billing/status` | Current subscription status |

**New database table:**
```sql
CREATE TABLE subscriptions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'free',  -- free, active, past_due, cancelled
    plan TEXT NOT NULL DEFAULT 'free',
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);
```

**Dependencies to add:**
```toml
# backend/pyproject.toml
stripe = ">=10.0.0"
```

### 6.3 Clerk + Stripe linking

On first login (or via billing/checkout), create a Stripe Customer linked to Clerk user ID. Store mapping in `subscriptions` table.

### 6.4 Frontend changes

- Add billing page/modal with plan selection
- Add upgrade prompts on feature-gated actions
- Add Stripe.js for checkout redirect

**Estimated effort:** 6-8 hours (full billing flow)

---

## Phase 5: CI/CD Pipeline

**Goal:** Automated build and deploy on push to main.

### 5.1 GitHub Actions workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure

on:
  push:
    branches: [main]
    paths-ignore:
      - 'landing/**'
      - 'docs/**'
      - '*.md'

permissions:
  id-token: write   # OIDC auth to Azure
  contents: read

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Login to ACR
        run: az acr login --name umcontainerreg

      - name: Build and push backend
        run: |
          docker build -t umcontainerreg.azurecr.io/um-backend:${{ github.sha }} ./backend
          docker build -t umcontainerreg.azurecr.io/um-backend:latest ./backend
          docker push umcontainerreg.azurecr.io/um-backend:${{ github.sha }}
          docker push umcontainerreg.azurecr.io/um-backend:latest

      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name um-backend \
            --resource-group rg-unstructured-minds \
            --image umcontainerreg.azurecr.io/um-backend:${{ github.sha }}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22

      - name: Build frontend
        working-directory: frontend
        env:
          VITE_API_URL: ${{ vars.VITE_API_URL }}
          VITE_CLERK_PUBLISHABLE_KEY: ${{ vars.VITE_CLERK_PUBLISHABLE_KEY }}
        run: |
          npm ci
          npm run build

      - name: Deploy to Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_SWA_TOKEN }}
          action: upload
          app_location: frontend/dist
          skip_app_build: true
```

### 5.2 GitHub secrets to configure

| Secret | Source |
|--------|--------|
| `AZURE_CLIENT_ID` | Entra app registration |
| `AZURE_TENANT_ID` | Entra tenant |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription |
| `AZURE_SWA_TOKEN` | Static Web App deployment token |

| Variable (non-secret) | Value |
|----------------------|-------|
| `VITE_API_URL` | `https://um-backend.<region>.azurecontainerapps.io` |
| `VITE_CLERK_PUBLISHABLE_KEY` | `pk_live_...` |

**Estimated effort:** 2-3 hours

---

## Migration Order

```
Phase 0 ──▶ Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5 ──▶ Phase 6
  Terraform    Postgres    Backend     Frontend     Clerk        CI/CD       Stripe
  + Entra      migration   deploy      deploy       production   pipeline    billing
  + tooling                                         (invite-only)            (later)

  2-3h          2-3h        3-4h        1-2h         2-3h        2-3h        6-8h
```

**Total: ~18-26 hours across all phases**

Phases 0-3 get you running on Azure. Phases 4-5 are production hardening. Phase 6 (Stripe) is deferred until you're ready to charge.

---

## Year-1 Exit Strategy (If Needed)

Azure PostgreSQL Flexible Server is free for 12 months. If you need to move off:

**Option A: Back to Neon (free tier, 0.5GB)**
```bash
pg_dump "postgresql://umadmin:***@um-postgres.postgres.database.azure.com/unstructured_minds" > backup.sql
# Create new Neon project, restore
psql "$NEON_URL" < backup.sql
# Update DATABASE_URL in Container Apps
```

**Option B: Supabase (free tier, 500MB)**
Same pg_dump/restore flow. Both support standard PostgreSQL.

**Option C: Stay on Azure (~$15/mo)**
The B1ms tier is reasonable for 10 users. No migration needed.

The app's Postgres usage is standard SQL (no extensions, no pgvector, no exotic types), so moving between any Postgres provider is a straightforward dump/restore.

---

## Environment Variables (Final State)

```env
# Azure PostgreSQL
DATABASE_URL=postgresql://umadmin:***@um-postgres.postgres.database.azure.com/unstructured_minds?sslmode=require

# Clerk Production
CLERK_SECRET_KEY=sk_live_...
CLERK_DOMAIN=clerk.unstructuredminds.com
VITE_CLERK_PUBLISHABLE_KEY=pk_live_...

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...

# Claude API (unchanged)
ANTHROPIC_API_KEY=sk-ant-...

# App
USE_CLOUD=true
CORS_ORIGINS=https://app.unstructuredminds.com
```

---

## Checklist

### Phase 0: Prerequisites + Terraform Foundation
- [ ] Azure account created (new = free tier eligible)
- [ ] Azure CLI installed and authenticated (`az login`)
- [ ] Terraform installed
- [ ] Terraform state storage bootstrapped (Storage Account — only manual step)
- [ ] `main.tf` + `variables.tf` + `resource_group.tf` + `entra.tf` written
- [ ] `terraform init && terraform apply` — resource group + Entra OIDC created
- [ ] GitHub secrets configured with Entra OIDC credentials

### Phase 1: Database (terraform apply)
- [ ] `postgres.tf` written
- [ ] `terraform apply` — PostgreSQL Flexible Server provisioned (B1ms, 32GB, free 12mo)
- [ ] pg_dump from Neon
- [ ] pg_restore to Azure PostgreSQL
- [ ] Verify data integrity (row counts, spot checks)
- [ ] Update DATABASE_URL
- [ ] Test app locally against Azure PostgreSQL

### Phase 2: Backend (terraform apply)
- [ ] `registry.tf` + `container_apps.tf` written
- [ ] `terraform apply` — Container Registry + Container Apps created
- [ ] Backend image built and pushed
- [ ] Backend deployed with secrets
- [ ] Health checks passing
- [ ] Test API endpoints from browser

### Phase 3: Frontend (terraform apply)
- [ ] `static_web_app.tf` written
- [ ] `terraform apply` — Static Web App created
- [ ] staticwebapp.config.json added
- [ ] Frontend built with production VITE_API_URL
- [ ] Deployed and SPA routing working
- [ ] Custom domain configured (optional)

### Phase 4: Clerk Production
- [ ] Production Clerk instance created
- [ ] Keys rotated in Container Apps secrets
- [ ] Frontend rebuilt with production publishable key
- [ ] CSP updated for production Clerk domain
- [ ] Invitation-only mode enabled (Restrictions → Restrict sign-ups → Invitation only)
- [ ] Test invitation flow (send invite, verify signup link works)
- [ ] User data remapped (if needed)
- [ ] Test full auth flow (sign in, sign out, blocked public sign-up)

### Phase 5: CI/CD
- [ ] GitHub Actions workflow created
- [ ] OIDC credentials configured in GitHub secrets (from Phase 0)
- [ ] Test: push to main triggers deploy
- [ ] Verify both frontend and backend deploy correctly
- [ ] `terraform plan` shows no drift (all resources managed)

### Phase 6: Stripe (when ready)
- [ ] Stripe account created
- [ ] Products and prices configured
- [ ] Webhook endpoint registered
- [ ] billing.py endpoints implemented
- [ ] Subscription table created
- [ ] Frontend billing UI added
- [ ] Test checkout flow with Stripe test mode
- [ ] Switch to Stripe live mode
