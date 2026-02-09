# Unstructured Minds - Deployment Strategy

## From Local Tool to Multi-Tenant SaaS

This folder contains the complete strategy for launching Unstructured Minds as a public web app with social login, per-user data isolation, and cloud deployment.

## Documents

| Document | What It Covers |
|----------|---------------|
| [01-architecture.md](./01-architecture.md) | Multi-tenant architecture, what changes from current single-user setup |
| [02-auth-and-users.md](./02-auth-and-users.md) | Google/social login, session management, user profiles |
| [03-data-strategy.md](./03-data-strategy.md) | Per-user DuckDB, Google Drive sync, data isolation |
| [04-deployment.md](./04-deployment.md) | Vercel + Railway setup, CI/CD, domain config |
| [05-anthropic-token-strategy.md](./05-anthropic-token-strategy.md) | API key management, usage limits, billing models |
| [06-landing-page.md](./06-landing-page.md) | Landing page design, copy, conversion flow |
| [07-implementation-roadmap.md](./07-implementation-roadmap.md) | Phased rollout plan with priorities and effort estimates |
| [08-cost-estimate.md](./08-cost-estimate.md) | Monthly costs at different user scales |

## Quick Decision Summary

| Decision | Choice | Why |
|----------|--------|-----|
| Frontend hosting | **Vercel** | Free tier, instant deploys, great DX |
| Backend hosting | **Railway** | Native Docker support, easy Python/FastAPI |
| Auth provider | **Clerk** | Drop-in Google login, no auth code to write |
| User data storage | **Per-user DuckDB on S3** | Isolation by design, cheap, familiar |
| File storage | **Google Drive API** | Users own their notes, zero storage cost for us |
| Anthropic API | **Hybrid: free tier + BYO key** | Low barrier to try, scales without killing margins |
| Database (app-level) | **Supabase Postgres** | User accounts, usage tracking, free tier |

## Architecture at a Glance

```
                    Vercel (Frontend)
                         |
                    Clerk (Auth)
                         |
                  Railway (FastAPI)
                    /    |    \
            Supabase  S3/R2   Google Drive
            (users)  (DuckDB)  (user files)
```
