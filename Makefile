# Repo-root Makefile shim. Most targets run inside the backend/ Compose stack;
# a few targets (baseline checks, host-only scripts) run on the host.
# Mirrors the targets in the technical guide I.2.5.

COMPOSE := docker compose -f backend/compose.yaml --project-directory backend

# Python on the host — used for host-only static checks. Override via:
#     make check PYTHON=py
# on Windows if `python` isn't on PATH.
PYTHON ?= python

.PHONY: help build up down logs ps shell dbshell test test-fast \
        lint lint-ruff lint-mypy lint-service-discipline \
        frontend-typecheck frontend-build frontend-shell \
        format migrate makemigrations seed-dev seed-dev-reset \
        check check-user-model clean dev-setup createsuperuser

help:
	@echo "MyPipelineHero — local development"
	@echo ""
	@echo "  make dev-setup                 One-command first-time setup (Linux/macOS)"
	@echo "  make build                     Build local Docker images"
	@echo "  make up                        Start the local stack"
	@echo "  make down                      Stop the local stack"
	@echo "  make logs                      Tail web/worker/beat logs"
	@echo "  make ps                        List running services"
	@echo "  make shell                     Django shell inside the web container"
	@echo "  make dbshell                   psql against local Postgres"
	@echo "  make test                      Run the pytest suite"
	@echo "  make test-fast                 Fast subset (no slow/e2e)"
	@echo "  make lint                      ruff + mypy + service-discipline (advisory)"
	@echo "  make lint-ruff                 ruff only"
	@echo "  make lint-mypy                 mypy only"
	@echo "  make lint-service-discipline   AST service-layer discipline (advisory in M0)"
	@echo "  make frontend-typecheck        tsc --noEmit (inside vite container)"
	@echo "  make frontend-build            vite build (inside vite container)"
	@echo "  make frontend-shell            sh inside the vite container"
	@echo "  make format                    ruff format + ruff --fix"
	@echo "  make migrate                   Apply Django migrations"
	@echo "  make makemigrations            Generate new migrations"
	@echo "  make seed-dev                  Apply migrations + seed demo tenant"
	@echo "  make seed-dev-reset            Same as seed-dev but with --reset"
	@echo "  make check                     django-check + host-side user-model baseline"
	@echo "  make check-user-model          Host-side user-model baseline only"
	@echo "  make clean                     Stop and remove all volumes (DESTRUCTIVE)"

# -----------------------------------------------------------------------------
# Stack
# -----------------------------------------------------------------------------

dev-setup:
	bash scripts/dev-setup.sh

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

createsuperuser: 
	$(COMPOSE) exec web python manage.py createsuperuser

# -----------------------------------------------------------------------------
# Tests + lint
# -----------------------------------------------------------------------------

test:
	$(COMPOSE) exec -T web pytest

test-fast:
	$(COMPOSE) exec -T web pytest -x -q -m "not slow and not e2e"

lint: lint-ruff lint-mypy lint-service-discipline

lint-ruff:
	$(COMPOSE) exec -T web ruff check apps config

lint-mypy:
	$(COMPOSE) exec -T web mypy

# Service-layer discipline (A.4.5). Advisory in M0 — always exits 0.
# Promoted to blocking from M2.
lint-service-discipline:
	$(PYTHON) scripts/check_service_layer_discipline.py

# -----------------------------------------------------------------------------
# Frontend (Phase 1 Vite + Tailwind 4 + TS)
# -----------------------------------------------------------------------------
#
# node_modules lives in a Docker named volume (see compose.yaml) so the
# native binaries match the Linux Alpine container. There is no host
# install step; npm install runs once inside the container when it first
# starts. Subsequent starts reuse the cached volume.
#
# Editor IntelliSense on frontend/ won't see node_modules unless you also
# do a host install. That is optional and orthogonal to the dev loop.

frontend-typecheck:
	$(COMPOSE) exec -T vite npm run typecheck

frontend-build:
	$(COMPOSE) exec -T vite npm run build

frontend-shell:
	$(COMPOSE) exec vite sh

# -----------------------------------------------------------------------------
# Formatting + migrations + seeding
# -----------------------------------------------------------------------------

format:
	$(COMPOSE) exec -T web ruff check --fix apps config
	$(COMPOSE) exec -T web ruff format apps config

migrate:
	$(COMPOSE) exec -T web python manage.py migrate

makemigrations:
	$(COMPOSE) exec -T web python manage.py makemigrations

seed-dev:
	$(COMPOSE) exec -T web python manage.py migrate
	$(COMPOSE) exec -T web python manage.py seed_dev_tenant

seed-dev-reset:
	$(COMPOSE) exec -T web python manage.py migrate
	$(COMPOSE) exec -T web python manage.py seed_dev_tenant --reset

# -----------------------------------------------------------------------------
# Checks + cleanup
# -----------------------------------------------------------------------------

check: check-user-model
	$(COMPOSE) exec -T web python manage.py check

check-user-model:
	$(PYTHON) scripts/check_user_model_baseline.py

clean:
	$(COMPOSE) down -v