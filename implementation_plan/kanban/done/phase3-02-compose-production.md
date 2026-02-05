# Docker Compose Production Setup

**Phase:** 3 - Deployment
**Priority:** High
**Status:** In Progress

## Description

Create production docker-compose configuration with proper networking, volumes, and environment handling.

## Tasks

- [ ] docker-compose.yml for production
- [ ] docker-compose.dev.yml for development
- [ ] Configure internal networking
- [ ] Volume mounts for data persistence
- [ ] Environment variable handling
- [ ] Resource limits
- [ ] Restart policies

## Acceptance Criteria

- `docker-compose up -d` starts all services
- Services communicate over internal network
- Data persists across container restarts
- Proper resource limits configured
- Graceful shutdown works

## docker-compose.yml

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - vault_data:/app/vault
      - db_data:/app/data
    environment:
      - ANTHROPIC_API_KEY
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G

volumes:
  vault_data:
  db_data:
```
