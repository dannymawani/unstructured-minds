# Nginx Production Configuration

**Phase:** 3 - Deployment
**Priority:** Medium
**Status:** Not Started

## Description

Configure nginx as reverse proxy with proper caching, compression, and API proxying.

## Tasks

- [ ] nginx.conf for frontend container
- [ ] Gzip compression
- [ ] Static file caching headers
- [ ] API proxy to backend
- [ ] SPA fallback routing
- [ ] Security headers

## Acceptance Criteria

- Static files served with cache headers
- API calls proxied to backend
- SPA routes work on refresh
- Compression enabled
- Security headers present

## nginx.conf

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;

    # Gzip
    gzip on;
    gzip_types text/css application/javascript application/json;

    # Static files
    location /assets {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
}
```
