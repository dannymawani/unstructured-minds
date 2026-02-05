# Security Hardening

**Phase:** 5 - Extensibility
**Priority:** High
**Status:** Not Started

## Description

Implement security best practices for production deployment.

## Tasks

- [ ] API rate limiting
- [ ] Input validation everywhere
- [ ] SQL injection prevention audit
- [ ] XSS prevention audit
- [ ] Secure headers
- [ ] API key rotation
- [ ] Dependency vulnerability scanning

## Acceptance Criteria

- Rate limiting prevents abuse
- All inputs validated and sanitized
- No SQL injection possible
- Security headers on all responses
- Dependencies scanned in CI

## Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/search")
@limiter.limit("100/minute")
async def search():
    ...
```

## Security Headers

```nginx
add_header X-Frame-Options "DENY";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Content-Security-Policy "default-src 'self'";
add_header Referrer-Policy "strict-origin-when-cross-origin";
```

## Dependency Scanning

```yaml
# CI job
- run: pip-audit
- run: npm audit
```
