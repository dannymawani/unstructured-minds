# Security

Security overview and guidelines for the Unstructured Minds application.

## Architecture Overview

Unstructured Minds is a **local-first, single-user application**. It is designed to run on a user's own machine or private network. There is no multi-user authentication system because the threat model assumes the operator is the sole user.

All data stays local -- notes live on disk, extracted data lives in a local DuckDB file, and the only external communication is with the Anthropic API for AI features.

## Security Measures

### Read-Only SQL Validation

All natural language queries are translated to SQL by Claude and then validated before execution. The validation layer enforces:

- Queries must begin with `SELECT` or `WITH` (CTEs).
- Dangerous keywords are blocked: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`, `REVOKE`, `EXEC`, `EXECUTE`, `ATTACH`, `DETACH`, `COPY`, `LOAD`, `INSTALL`, `PRAGMA`, `CALL`, `SET`, `EXPLAIN`.
- Multiple statements (semicolons mid-query) are rejected.
- Results are capped at 100 rows.

### Rate Limiting

All API endpoints are rate-limited using slowapi to prevent abuse:

- Claude API endpoints have stricter limits to control costs.
- Search endpoints are rate-limited to prevent excessive file system reads.
- Standard CRUD endpoints have generous but bounded limits.

### CORS

Cross-Origin Resource Sharing is configured to allow only specific origins. By default, only `http://localhost:3000` and `http://localhost:5173` are permitted. Origins are configurable via the `CORS_ORIGINS` environment variable.

### Security Headers

A custom middleware adds security headers to every response:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Input Validation

All API request bodies are validated using Pydantic models with:

- Maximum length constraints on query strings and text inputs.
- Type validation on all fields.
- Field-level constraints (min/max values, allowed patterns).

## Known Limitations

- **No authentication.** This is a single-user local application. If you expose the API to a network, anyone with access can read and modify your data.
- **No encryption at rest.** The DuckDB database and vault files are stored as plain files on disk. Use full-disk encryption (FileVault, LUKS, BitLocker) if this is a concern.
- **API key in environment.** The Anthropic API key is stored in an environment variable or `.env` file. It is not encrypted.

## Deployment Checklist

1. **Set the API key securely.** Use environment variables or Docker secrets rather than committing the key to source control. Never check `.env` files into git.
2. **Configure CORS for production.** Set `CORS_ORIGINS` to the exact origin(s) your frontend is served from. Do not use wildcards.
3. **Use Docker for isolation.** Running the application in containers provides process-level isolation and limits file system access.
4. **Do not expose ports to the public internet.** This application is designed for local or private network use. If you must expose it, place it behind a reverse proxy with authentication (e.g., nginx with basic auth or an OAuth proxy).
5. **Keep dependencies updated.** Regularly update Python packages and Docker base images to pick up security patches.

## Reporting Security Issues

If you discover a security vulnerability, please report it privately rather than opening a public issue. Contact the maintainers directly so the issue can be assessed and addressed before disclosure.
