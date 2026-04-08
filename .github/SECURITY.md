# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| `main`  | ✅ Latest release  |

Older tagged releases do not receive backported security fixes. Please update to the latest version on `main`.

---

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, use one of these channels:

### Option 1: GitHub Private Vulnerability Reporting (preferred)

1. Go to the **Security** tab of this repository
2. Click **"Report a vulnerability"**
3. Fill out the form with as much detail as possible

### Option 2: Email

Send a description to the maintainer via the email on the GitHub profile.

---

### What to Include

A good vulnerability report includes:

- **Description** — what the vulnerability is and its potential impact
- **Steps to reproduce** — a minimal reproduction case
- **Environment** — OS, Docker version, storage mode (`local` / `postgres`), auth mode
- **Affected component** — backend API, frontend, database layer, auth, etc.
- **Suggested fix** — if you have one

---

### Response Timeline

| Event | Target |
|-------|--------|
| Acknowledgement | Within 48 hours |
| Initial assessment | Within 7 days |
| Fix / disclosure | Within 30 days (depending on severity) |

---

## Security Model & Scope

This project is designed primarily for **personal, local use**. Understanding the intended threat model helps set expectations:

### Local Mode (default)

- Runs on `localhost` — no authentication by default
- Assumes a trusted environment (your own machine or LAN)
- No user accounts or multi-tenancy
- All data stays on your machine (DuckDB file)

### Postgres / Multi-user Mode

- Supports `basic` auth (HTTP Basic) or `clerk` (JWT via Clerk.com)
- User data is isolated by `user_id`
- DuckDB runs in-memory as an analytics cache

### In Scope

| Area | Details |
|------|---------|
| Authentication bypass | Bypassing `basic` or `clerk` auth |
| SQL injection | In DuckDB natural language query pipeline |
| Path traversal | In vault/file API endpoints |
| SSRF | Via LLM proxy or webhook integrations |
| Secret exposure | API keys leaking via responses or logs |
| Privilege escalation | Cross-user data access in multi-user mode |
| Dependency vulnerabilities | In `requirements.txt` / `package.json` |

### Out of Scope

| Area | Reason |
|------|--------|
| Missing auth on `localhost` | By design — local mode is unauthenticated |
| CORS for `localhost` origins | Expected for local development |
| Self-XSS | User controls their own vault content |
| Rate limiting | Not in scope for local deployment |
| Issues requiring physical access | Out of threat model |
| Vulnerabilities in unreleased branches | Only `main` is supported |

---

## Security Hardening

If you are deploying this beyond a single trusted machine, review [`docs/SECURITY.md`](https://github.com/dannymawani/unstructured-minds/blob/main/docs/SECURITY.md) for:

- Enabling authentication (`AUTH_MODE=basic` or `AUTH_MODE=clerk`)
- Setting `CORS_ORIGINS` to only your trusted origins
- Running behind a reverse proxy (nginx/Caddy) with TLS
- Using Tailscale for zero-config encrypted remote access
- Keeping your LLM API key out of logs and version control

---

## Disclosure Policy

We follow **coordinated disclosure**:

1. Reporter submits privately
2. Maintainer confirms and assesses severity
3. Fix is developed and tested
4. Fix is released and reporter is credited (unless anonymity is requested)
5. Public disclosure after fix is available

---

## Hall of Fame

Security researchers who responsibly disclose valid vulnerabilities will be credited here (with permission).

*No entries yet — be the first!*
