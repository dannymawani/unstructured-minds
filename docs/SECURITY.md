# Security

Security overview and guidelines for the Unstructured Minds application.

## Architecture Overview

Unstructured Minds is a **local-first application** designed to run on a user's own machine or private network. It supports three authentication modes (`none`, `basic`, `clerk`) to accommodate different deployment scenarios -- from single-user local use to multi-user cloud deployments.

In local mode, all data stays on your machine -- notes live on disk, extracted data lives in a local DuckDB file, and the only external communication is with your configured LLM provider (Anthropic, OpenAI, Ollama, etc.) for AI features.

## Authentication

| Mode | How it works | Multi-user |
|------|-------------|------------|
| `none` (default) | No auth. Single implicit user. | No |
| `basic` | HTTP Basic Auth (username/password from env vars) | No |
| `clerk` | Clerk JWT verification, per-user data isolation | Yes |

See [`docs/AUTH.md`](./AUTH.md) for full setup instructions.

## Security Measures

### Read-Only SQL Validation (Defense-in-Depth)

Natural language queries are translated to SQL by the LLM and validated through 4 layers before execution:

1. **System prompt separation** -- SQL generation uses isolated system prompts with anti-injection rules
2. **`validate_sql()`** -- Keyword deny-list, function deny-list, system table blocking, DuckDB parser (exactly 1 statement)
3. **`read_only_execute()`** -- Wraps in `BEGIN TRANSACTION` / `ROLLBACK`, materializes results before rollback
4. **Auto LIMIT 100** on all results

Blocked keywords include: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`, `REVOKE`, `EXEC`, `EXECUTE`, `ATTACH`, `DETACH`, `COPY`, `LOAD`, `INSTALL`, `PRAGMA`, `CALL`, `SET`, `EXPLAIN`.

### Rate Limiting

All API endpoints are rate-limited using slowapi:

- LLM-calling endpoints: 20-30/min (controls costs)
- Search endpoints: 100/min
- Export/Import: 5/min
- Standard CRUD: generous but bounded

### CORS

Cross-Origin Resource Sharing is configured to allow only specific origins. By default, only `http://localhost:3000` and `http://localhost:5173` are permitted. Configurable via `CORS_ORIGINS` environment variable. Never use wildcards.

### Security Headers

Defined in `frontend/nginx/security-headers.conf` (single source of truth):

- Content-Security-Policy (CSP)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Input Validation

All API request bodies are validated using Pydantic models with:

- Maximum length constraints on query strings and text inputs
- Type validation on all fields
- Field-level constraints (min/max values, allowed patterns)
- Path traversal prevention (no `..` in file paths)

## Known Limitations

- **No encryption at rest.** The DuckDB database and vault files are stored as plain files on disk. Use full-disk encryption (FileVault, LUKS, BitLocker) if this is a concern.
- **API key in environment.** LLM API keys are stored in environment variables or `.env` file. They are not encrypted.
- **Basic auth password in plaintext.** The `BASIC_AUTH_PASSWORD` env var is not hashed. Suitable for Tailscale/private network, not for internet-facing deployments.
- **No HTTPS by default.** Use Tailscale (WireGuard encryption) or place behind a TLS-terminating reverse proxy.

## Deployment Checklist

1. **Set API keys securely.** Use environment variables or Docker secrets. Never commit `.env` files to git.
2. **Configure CORS for production.** Set `CORS_ORIGINS` to exact origin(s). No wildcards.
3. **Use Docker for isolation.** Containers provide process-level isolation and limit file system access.
4. **Do not expose ports to the public internet.** Use Tailscale for remote access, or place behind a reverse proxy with authentication.
5. **Keep dependencies updated.** Regularly update Python packages and Docker base images.
6. **Enable authentication.** Use at minimum `AUTH_MODE=basic` when exposing over any network.

## Reporting Security Issues

If you discover a security vulnerability, please report it privately rather than opening a public issue. Contact the maintainers directly so the issue can be assessed and addressed before disclosure.
