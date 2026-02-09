# 07 - Implementation Roadmap

## Phase Overview

```
Phase 0: Foundation        (1-2 weeks)    ← Do this first
Phase 1: Auth + Multi-tenant (2-3 weeks)  ← Core architecture change
Phase 2: Google Drive       (1-2 weeks)    ← Replace local filesystem
Phase 3: Landing + Polish   (1-2 weeks)    ← Public-facing
Phase 4: Billing + Launch   (1 week)       ← Go live
────────────────────────────────────────────
Total: ~6-10 weeks to launch MVP
```

## Phase 0: Foundation (Week 1-2)

**Goal**: Set up all external services and get a "hello world" deploy working.

### Tasks

- [ ] **Register domain**: `unstructuredminds.com` (Cloudflare Registrar or Namecheap)
- [ ] **Clerk setup**: Create project, configure Google OAuth provider, get API keys
- [ ] **Supabase setup**: Create project, run user/usage table migrations
- [ ] **Cloudflare R2 setup**: Create bucket, generate API tokens
- [ ] **Railway setup**: Create project, deploy current backend Docker image
- [ ] **Vercel setup**: Connect repo, deploy current frontend as-is
- [ ] **DNS**: Point domain to Vercel, `api.` subdomain to Railway
- [ ] **Verify**: Both frontend and backend accessible at custom domain (even if no auth yet)

### Deliverable
The current app running at `unstructuredminds.com/app` and `api.unstructuredminds.com` with no auth. Proves the infrastructure works.

---

## Phase 1: Auth + Multi-Tenant (Week 2-4)

**Goal**: Users can sign in with Google. Each user gets isolated data.

### Frontend Tasks

- [ ] **Install Clerk SDK**: `npm install @clerk/clerk-react`
- [ ] **Add ClerkProvider** to `main.tsx`
- [ ] **Create route structure**:
  - `/` → Landing page placeholder
  - `/app/*` → Protected app routes (current app)
  - `/login` → Clerk SignIn component
- [ ] **Modify `apiClient.ts`**: Include Clerk session token in all API calls
- [ ] **Add UserButton**: Show user avatar + sign-out in sidebar
- [ ] **Usage display**: Show remaining AI quota in settings

### Backend Tasks

- [ ] **Auth middleware**: Verify Clerk JWT, extract `user_id`
- [ ] **Apply middleware** to all routes except `/health` and `/webhooks/*`
- [ ] **Clerk webhook handler**: Provision new users on `user.created`
- [ ] **User database manager**: Load/save per-user DuckDB from R2
  - Implement R2 upload/download
  - LRU cache for in-memory connections
  - Auto-save dirty databases on request completion
- [ ] **User settings from Supabase**: Replace `settings.json` with DB lookup
- [ ] **Usage tracking**: Log every AI call with token counts
- [ ] **Quota enforcement**: Check limits before AI calls
- [ ] **Config refactor**: Add new env vars for Clerk, Supabase, R2, Redis

### Database Tasks

- [ ] **Supabase migrations**: Create users, usage_log, user_settings tables
- [ ] **DuckDB provisioning**: Script to create empty user database with schema
- [ ] **Data migration script**: Convert your current data to first tenant's data

### Deliverable
You can sign in with Google. Your data is loaded from R2. A new test user gets a fresh empty database. Usage is tracked.

---

## Phase 2: Google Drive Integration (Week 4-6)

**Goal**: User notes live in Google Drive, not local filesystem.

### Tasks

- [ ] **Google OAuth scopes**: Configure Clerk to request `drive.file` scope
- [ ] **GoogleDriveVault class**: Implements same interface as current filesystem vault
  - `list_files()`, `read_file()`, `write_file()`, `delete_file()`
  - Path resolution (folder name → Drive folder ID)
  - Create folder structure on first use
- [ ] **CachedDriveVault**: Redis caching layer over Drive API
- [ ] **Replace vault operations**: Swap all filesystem calls with Drive API calls
- [ ] **Drive webhook**: Listen for changes when users edit in Drive directly
- [ ] **File tree update**: Frontend file tree works with Drive-backed files
- [ ] **Template sync**: Copy default templates to user's Drive on signup
- [ ] **Upstash Redis setup**: Deploy and connect caching layer

### Migration Task

- [ ] **Your vault migration**: Upload your current `vault/` files to your Google Drive

### Deliverable
Creating, editing, and reading notes all go through Google Drive. Files appear in the user's Drive. Cache keeps things fast.

---

## Phase 3: Landing Page + Polish (Week 6-8)

**Goal**: Public-facing landing page. Polished onboarding.

### Landing Page Tasks

- [ ] **Landing page**: Hero, How It Works, Features, Use Cases, Pricing
- [ ] **Pricing page**: Free / BYO Key / Pro comparison
- [ ] **SEO**: Meta tags, OG image, pre-rendering for landing page
- [ ] **Responsive**: Mobile-friendly landing page
- [ ] **Privacy Policy**: Required for Google OAuth verification
- [ ] **Terms of Service**: Required for public launch

### Onboarding Tasks

- [ ] **Welcome flow**: After first Google login → quick setup wizard
  - "Choose your template" (fitness, wellness, general)
  - "Here's your first daily note"
  - Quick feature tour (3-4 tooltips)
- [ ] **BYO Key setup**: Settings page for adding Anthropic key
- [ ] **Usage dashboard**: Show operations used this month
- [ ] **Upgrade prompts**: When quota runs low, show upgrade options

### Polish Tasks

- [ ] **Loading states**: Skeleton screens while DuckDB loads from R2
- [ ] **Error boundaries**: Graceful errors for Drive API failures
- [ ] **Offline detection**: Show banner when API unreachable
- [ ] **Mobile responsive**: App layout works on tablet/phone

### Deliverable
A visitor can land on `unstructuredminds.com`, understand what it does, sign up, and start using it within 2 minutes.

---

## Phase 4: Billing + Launch (Week 8-9)

**Goal**: Stripe integration. Pro tier. Public announcement.

### Tasks

- [ ] **Stripe setup**: Create products (Pro $12/mo)
- [ ] **Stripe Checkout**: Upgrade flow from within the app
- [ ] **Stripe webhooks**: Handle subscription created/cancelled/payment_failed
- [ ] **Tier enforcement**: Pro users get 500 ops, free get 50
- [ ] **Customer portal**: Link to Stripe portal for managing subscription
- [ ] **Email**: Welcome email on signup (Clerk handles this)
- [ ] **Analytics**: Add Plausible (privacy-friendly) or PostHog
- [ ] **Launch**: Post on relevant communities, social media

### Deliverable
Live product with payment processing. Ready for real users.

---

## Phase 5: Post-Launch (Ongoing)

- [ ] **Apple Sign-In**: Add to Clerk config
- [ ] **GitHub Sign-In**: Add to Clerk config
- [ ] **DuckDB-WASM**: Move read queries to browser for faster dashboard
- [ ] **Collaboration**: Shared notes between users (future)
- [ ] **Mobile app**: PWA or React Native wrapper (future)
- [ ] **Custom domains**: Allow users to use their own domain (enterprise)

---

## Priority Order (If Short on Time)

If you want to launch as fast as possible, here's what to cut:

### MVP (4 weeks)

1. Clerk auth with Google login
2. Per-user DuckDB on R2 (skip Google Drive initially - use R2 for files too)
3. Basic landing page (Hero + CTA only)
4. BYO key only (skip our API key / billing entirely)
5. Deploy on Vercel + Railway

This gets you a working multi-user app where people bring their own Anthropic key. No billing complexity. No Google Drive API. Just auth + data isolation.

### Then Layer On

6. Google Drive integration
7. Free tier with platform key
8. Stripe billing for Pro
9. Full landing page
10. Polish and onboarding

## Critical Path

```
Domain + DNS ──┐
Clerk setup ───┤
Supabase setup ┼──► Auth middleware ──► Per-user DuckDB ──► Landing page ──► Launch
R2 setup ──────┤                            │
Railway setup ─┘                    Google Drive (can be parallel)
```

The bottleneck is auth middleware + per-user DuckDB. Everything else can be parallelized.
