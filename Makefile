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
        frontend-install frontend-install-host-only \
        frontend-typecheck frontend-build frontend-shell \
        format migrate makemigrations seed-dev \
        check check-user-model clean

help:
	@echo "MyPipelineHero — local development"
	@echo ""
	@echo "  make build                       Build local Docker images"
	@echo "  make up                          Start the local stack"
	@echo "  make down                        Stop the local stack"
	@echo "  make logs                        Tail web/worker/beat logs"
	@echo "  make ps                          List running services"
	@echo "  make shell                       Django shell inside the web container"
	@echo "  make dbshell                     psql against local Postgres"
	@echo "  make test                        Run the pytest suite"
	@echo "  make test-fast                   Fast subset (no slow/e2e)"
	@echo "  make lint                        ruff + mypy + service-discipline (advisory)"
	@echo "  make lint-ruff                   ruff only"
	@echo "  make lint-mypy                   mypy only"
	@echo "  make lint-service-discipline     AST service-layer discipline (advisory in M0)"
	@echo "  make frontend-install            npm install on host with cross-platform optional deps"
	@echo "  make frontend-install-host-only  Quick reinstall — host platform binaries only"
	@echo "  make frontend-typecheck          tsc --noEmit (on host)"
	@echo "  make frontend-build              vite build (on host; produces frontend/dist/)"
	@echo "  make frontend-shell              sh inside the vite container"
	@echo "  make format                      ruff format + ruff --fix"
	@echo "  make migrate                     Apply Django migrations"
	@echo "  make makemigrations              Generate new migrations"
	@echo "  make seed-dev                    Run seed_v1 + seed_dev_tenant (D4)"
	@echo "  make check                       django-check + host-side user-model baseline"
	@echo "  make check-user-model            Host-side user-model baseline only"

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

lint: lint-ruff lint-mypy lint-service-discipline

lint-ruff:
	$(COMPOSE) exec -T web ruff check apps config

lint-mypy:
	$(COMPOSE) exec -T web mypy apps config

# Service-layer discipline (A.4.5). Advisory in M0 — always exits 0.
# Promoted to blocking from M2.
lint-service-discipline:
	$(PYTHON) scripts/check_service_layer_discipline.py

# Frontend (Phase 1 Vite + Tailwind 4 + TS) ---------------------------------
#
# These targets run on the HOST, not inside a container. Reason: on Windows
# + WSL2, container-side `npm install` against a bind-mounted volume can
# effectively stall on the thousands of tiny files in node_modules.
#
# The install is split into multiple passes because native-dep packages
# (rollup, lightningcss, @tailwindcss/oxide, esbuild) ship per-platform
# binaries as optional dependencies. The Vite dev server runs in a
# linux-x64-musl (Alpine) container; CI runs on linux-x64-gnu. Both
# platforms' binaries need to be on disk so the Linux container can load
# the right Rollup native module.
#
# Subsequent passes are additive — they install only missing optional
# deps for their target platform, leaving everything else in place.

frontend-install:
	@echo "Installing host platform binaries..."
	cd frontend && npm install --no-fund --no-audit
	@echo "Installing linux-x64-musl binaries (Alpine container)..."
	cd frontend && npm install --no-fund --no-audit --force --os=linux --cpu=x64 --libc=musl
	@echo "Installing linux-x64-gnu binaries (CI)..."
	cd frontend && npm install --no-fund --no-audit --force --os=linux --cpu=x64 --libc=glibc
	@echo ""
	@echo "Frontend install complete. Verify with:"
	@echo "  ls frontend/node_modules/@rollup/"
	@echo "  ls frontend/node_modules/@tailwindcss/"
	@echo "  ls frontend/node_modules/lightningcss-*"

frontend-install-host-only:
	cd frontend && npm install --no-fund --no-audit

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-build:
	cd frontend && npm run build

frontend-shell:
	$(COMPOSE) exec vite sh

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

check: check-user-model
	$(COMPOSE) exec -T web python manage.py check

check-user-model:
	$(PYTHON) scripts/check_user_model_baseline.py

clean:
	$(COMPOSE) down -v