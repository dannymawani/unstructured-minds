# Docker Configuration (Production)

**Phase:** 3 - Deployment
**Priority:** High
**Status:** Done

## Description

Create production-ready Docker configuration with multi-stage builds and optimized images.

## Tasks

- [ ] Backend Dockerfile (multi-stage)
- [ ] Frontend Dockerfile (build + nginx)
- [ ] Optimize image sizes
- [ ] Non-root user for security
- [ ] Health check commands
- [ ] Build arguments for config

## Acceptance Criteria

- `docker build backend/` succeeds
- `docker build frontend/` succeeds
- Images under 500MB each
- Health checks pass
- No root process

## Backend Dockerfile

```dockerfile
FROM python:3.14-slim AS builder
# Install dependencies

FROM python:3.14-slim
# Copy only what's needed
USER appuser
HEALTHCHECK CMD curl -f http://localhost:8000/health
```

## Frontend Dockerfile

```dockerfile
FROM node:22-alpine AS build
# Build static files

FROM nginx:alpine
# Serve with nginx
```
