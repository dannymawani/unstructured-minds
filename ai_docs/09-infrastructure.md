# Infrastructure

Docker, CI/CD, environment variables, cloud setup, backup/restore, and LAN access.

## Docker Compose

### Production (`docker-compose.yml`)

```yaml
services:
  backend:
    build: ./backend                    # python:3.13-slim multi-stage
    ports: ["8000:8000"]
    volumes:
      - ${VAULT_PATH:-./vault}:/app/vault:rw
      - ${DATA_PATH:-./data}:/app/data:rw
    environment:
      LLM_PROVIDER, LLM_API_KEY, LLM_MODEL_FAST, LLM_MODEL_SMART,
      ANTHROPIC_API_KEY (legacy), STORAGE_MODE, DATABASE_URL,
      AUTH_MODE, BASIC_AUTH_USERNAME, BASIC_AUTH_PASSWORD,
      VAULT_PATH=/app/vault, DATA_PATH=/app/data, HOST=0.0.0.0, PORT=8000, DEBUG,
      CLERK_SECRET_KEY, CLERK_DOMAIN
    healthcheck: curl -f http://localhost:8000/health (30s)
    networks: [app-network]

  frontend:
    build:
      context: ./frontend               # node:22-alpine → nginx:alpine
      args: [VITE_CLERK_PUBLISHABLE_KEY]
    ports: ["${FRONTEND_PORT:-3000}:80"]
    depends_on: backend (service_healthy)
    healthcheck: wget --spider http://localhost:80/nginx-health (30s)
    networks: [app-network]
```

### Development (`docker-compose.dev.yml`)

- Frontend: Vite dev server on port 5173 with hot reload
- Backend: FastAPI with `--reload` flag on port 8000
- Volumes: Live code reload

### Nginx (Production Frontend)

- Serves static React bundle from `/usr/share/nginx/html`
- Proxies `/api/*` → `http://backend:8000/`
- Gzip compression for assets
- SPA routing (try_files → `/index.html`)
- Long-lived cache for `/assets/`
- CSP headers via `nginx/security-headers.conf`

## Environment Variables

### Core

| Variable | Default | Purpose |
|----------|---------|---------|
| `VAULT_PATH` | `./vault` | Markdown notes directory |
| `DATA_PATH` | `./data` | DuckDB, settings, configs |
| `HOST` | `0.0.0.0` | API bind address |
| `PORT` | `8000` | API port |
| `FRONTEND_PORT` | `3000` | Nginx port (Docker) |
| `DEBUG` | `false` | Verbose logging + hot reload |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated |
| `LLM_PROVIDER` | — | LLM provider (anthropic, openai, ollama, etc.) |
| `LLM_API_KEY` | — | API key for the LLM provider |
| `LLM_MODEL_FAST` | — | Fast model override (default per provider) |
| `LLM_MODEL_SMART` | — | Smart model override (default per provider) |
| `AUTH_MODE` | `none` | Authentication: none / basic / clerk |

### Cloud Mode

| Variable | Required | Purpose |
|----------|----------|---------|
| `STORAGE_MODE` | `local` | `local` or `postgres` |
| `DATABASE_URL` | Yes* | `postgresql://user:pass@host:port/db` |
| `DB_POOL_MIN` / `DB_POOL_MAX` | No | Connection pool (default 2/10) |
| `BASIC_AUTH_USERNAME` | No** | Username for basic auth |
| `BASIC_AUTH_PASSWORD` | No** | Password for basic auth |
| `CLERK_SECRET_KEY` | No*** | JWT signing key |
| `CLERK_DOMAIN` | No*** | Clerk issuer domain |

\* Required when `STORAGE_MODE=postgres`
\*\* Required when `AUTH_MODE=basic`
\*\*\* Required when `AUTH_MODE=clerk`

### Frontend (Vite — baked into JS bundle at build time)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Backend URL (default `http://localhost:8000`, Docker: `/api`) |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk public key (**must be Docker build arg**) |
| `VITE_API_PROXY_TARGET` | Vite dev proxy target |

## Cloud Setup Scripts

All run from `backend/` directory:

| Command | Purpose |
|---------|---------|
| `python3 -m scripts.setup_cloud` | Full setup: schemas + seed vault + migrate DuckDB + migrate settings |
| `python3 -m scripts.setup_cloud --drop-first` | Wipe + rebuild everything |
| `python3 -m scripts.setup_cloud --skip-seed` | Schemas only (no data) |
| `python3 -m scripts.backup_to_local` | Full backup: Postgres → local DuckDB + vault + settings |
| `python3 -m scripts.backup_to_local --tables-only` | Data tables only |
| `python3 -m scripts.backup_to_local --vault-only` | Vault files only |
| `python3 -m scripts.backup_to_local --settings-only` | JSON settings only |
| `python3 -m scripts.migrate_duckdb_to_postgres` | DuckDB → Postgres migration |
| `python3 -m scripts.migrate_user_id` | Normalize user IDs to UUIDs |
| `python3 -m scripts.seed_vault` | Insert filesystem files into vault_files |

### Prerequisites

- `DATABASE_URL` must be set in `.env`
- Postgres server must be reachable
- For DuckDB migration: `data/unstructured.duckdb` must exist

## CI/CD

### GitHub Actions

- `.github/workflows/deploy-landing.yml` — Deploys the `website/` directory on push to main
- Path filter triggers on `website/**` changes

## LAN Access (Testing on Phone/Tablet)

1. Get Mac IP: `ipconfig getifaddr en0`
2. Set in `.env`:
   ```
   VITE_API_URL=http://192.168.x.x:8000
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://192.168.x.x:5173
   ```
3. Restart containers
4. Open `http://192.168.x.x:5173` on device

**Security:** Unencrypted HTTP — only use on trusted private network. Disable when done.

## Shell / Environment Notes

- **macOS zsh**: Always quote URLs with single quotes in `curl` commands — unquoted `?` and `&` trigger zsh globbing errors
- Use `python3` not `python` — only `python3` is on `PATH`

## Deployment Checklist

1. Set API key securely (env vars or Docker secrets, never committed)
2. Configure `CORS_ORIGINS` for exact production origin(s)
3. Use Docker for process isolation
4. Do not expose ports to public internet without reverse proxy + auth
5. Keep dependencies updated for security patches
