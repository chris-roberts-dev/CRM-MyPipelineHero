# Repo-root Makefile shim. All commands run from backend/ where compose.yaml lives.
# Mirrors the targets in the technical guide I.2.5.

COMPOSE := docker compose -f backend/compose.yaml --project-directory backend

.PHONY: help build up down logs ps shell dbshell test test-fast lint format \
        migrate makemigrations seed-dev check clean

help:
	@echo "MyPipelineHero — local development"
	@echo ""
	@echo "  make build           Build local Docker images"
	@echo "  make up              Start the local stack (web, worker, beat, postgres, redis, mailpit, minio, nginx)"
	@echo "  make down            Stop the local stack"
	@echo "  make logs            Tail web/worker/beat logs"
	@echo "  make ps              List running services"
	@echo "  make shell           Open a Django shell inside the web container"
	@echo "  make dbshell         Open psql against the local Postgres"
	@echo "  make test            Run the pytest suite"
	@echo "  make test-fast       Run a fast subset (no slow/e2e tests)"
	@echo "  make lint            Run ruff + mypy"
	@echo "  make format          Run ruff format + ruff --fix"
	@echo "  make migrate         Apply Django migrations"
	@echo "  make makemigrations  Generate new migrations"
	@echo "  make seed-dev        Run seed_v1 + seed_dev_tenant (M0 next deliverable / M1)"
	@echo "  make check           django-check + check_user_model_baseline.py"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f web worker beat

ps:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec web python manage.py shell

dbshell:
	$(COMPOSE) exec postgres psql -U mph mph

test:
	$(COMPOSE) exec -T web pytest

test-fast:
	$(COMPOSE) exec -T web pytest -x -q -m "not slow and not e2e"

lint:
	$(COMPOSE) exec -T web ruff check apps config
	$(COMPOSE) exec -T web mypy apps config

format:
	$(COMPOSE) exec -T web ruff check --fix apps config
	$(COMPOSE) exec -T web ruff format apps config

migrate:
	$(COMPOSE) exec -T web python manage.py migrate

makemigrations:
	$(COMPOSE) exec -T web python manage.py makemigrations

seed-dev:
	$(COMPOSE) exec -T web python manage.py seed_v1
	$(COMPOSE) exec -T web python manage.py seed_dev_tenant

check:
	$(COMPOSE) exec -T web python manage.py check
	$(COMPOSE) exec -T web python scripts/check_user_model_baseline.py

clean:
	$(COMPOSE) down -v
