# =============================================================================
# Unstructured Minds — Common Commands
# =============================================================================

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

up: ## Start in local mode (DuckDB, zero deps)
	docker compose up -d

up-postgres: ## Start with bundled Postgres
	docker compose --profile postgres up -d

down: ## Stop all services
	docker compose --profile postgres down

dev: ## Start dev mode with hot reload
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-postgres: ## Start dev mode with Postgres
	docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile postgres up

logs: ## Tail logs from all services
	docker compose logs -f

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build: ## Rebuild all containers
	docker compose build

build-no-cache: ## Rebuild without cache
	docker compose build --no-cache

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && python3 -m pytest

test-frontend: ## Run frontend tests
	cd frontend && npm test -- --run

typecheck: ## Run frontend type checking
	cd frontend && npm run typecheck

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

clean: ## Remove containers, volumes, and orphans
	docker compose --profile postgres down -v --remove-orphans

ps: ## Show running services
	docker compose ps

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: up up-postgres down dev dev-postgres logs build build-no-cache test test-backend test-frontend typecheck clean ps help
