.PHONY: help dev db-up db-down api web test test-api test-web lint lint-api lint-web format install

COMPOSE := docker compose -f infra/docker-compose.yml

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## Install API and web dependencies
	cd apps/api && uv sync
	cd apps/web && pnpm install

db-up: ## Start Postgres + pgvector and wait until healthy
	$(COMPOSE) up -d --wait db

db-down: ## Stop Postgres
	$(COMPOSE) down

api: ## Run the API with reload on :8000
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

web: ## Run the web dev server on :3000
	cd apps/web && pnpm dev

dev: db-up ## Start the database, API and web together
	$(MAKE) -j2 api web

test: test-api test-web ## Run all tests

test-api:
	cd apps/api && uv run pytest

test-web:
	cd apps/web && pnpm test

lint: lint-api lint-web ## Lint and typecheck both apps

lint-api:
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app

lint-web:
	cd apps/web && pnpm lint && pnpm typecheck

format: ## Auto-format both apps
	cd apps/api && uv run ruff check --fix . && uv run ruff format .
	cd apps/web && pnpm exec eslint --fix .
