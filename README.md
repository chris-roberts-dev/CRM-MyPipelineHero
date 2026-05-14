# MyPipelineHero

Multi-tenant CRM SaaS for organizations selling services, resale products, and
manufactured products.

This repository implements the architecture defined in
**`docs/guide.md`** (the MyPipelineHero technical development guide v0.7).
That guide is the authoritative source for architecture, terminology, domain
models, workflows, authentication, pricing, deployment, admin surfaces, and
milestone scope. Code in this repository is required to match the guide.

## Repository layout

```text
frontend/        # Phase 1 Vite + Tailwind 4 + TS assets; Phase 2 React lands in M9+
backend/         # Django project + apps
docs/            # Authoritative technical guide and retrospectives
scripts/         # CI / local-dev / safety scripts
```

For the canonical detailed layout see `docs/guide.md` § A.5.

## Phase posture

- **Phase 1** (M0–M8). Server-rendered Django + Tailwind 4 + HTMX tenant portal.
  Phase 1 ships the full CRM and serves real tenants.
- **Phase 2** (M9+). React tenant portal consumes a DRF internal API. Root-domain
  landing/auth pages, custom platform admin, custom tenant admin, support
  impersonation, and email templates remain server-rendered permanently.

## Required tooling

- Docker + Docker Compose v2 (`docker compose ...`)
- GNU Make
- (Optional) Node.js 20.x or 24.x on the host — only needed for editor
  IntelliSense; the Vite container does its own `npm install` into a Docker
  named volume.

You do not need a local Python install for application work; Python runs
through containers. A local Python 3.14 install plus `pip install -r
backend/requirements/dev.txt` is supported for editor/IDE tooling.

## First-time setup

### Linux / macOS

```bash
git clone <repo-url> mph
cd mph
make dev-setup
```

That script verifies tooling, adds `mph.local` to `/etc/hosts`, builds images,
brings the stack up, applies migrations (which runs `seed_v1`), runs
`seed_dev_tenant` to create the demo tenant, runs `pytest`, and prints the
URLs and credentials.

### Windows (PowerShell)

```powershell
git clone <repo-url> mph
cd mph

# Add mph.local to hosts (PowerShell as Administrator)
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "`n127.0.0.1 mph.local"

# Build, start, migrate, seed
make build
make up
make migrate
make seed-dev
make test
```

See "URLs and credentials" below for what to open afterward.

## URLs and credentials

After `make seed-dev` completes:

| URL | What it is |
| --- | --- |
| <http://mph.local/> | Public landing page |
| <http://mph.local/login/> | Login (scaffold only in M0; full flow in M1) |
| <http://mph.local/platform/> | Custom platform admin shell |
| <http://mph.local/django-admin/> | Raw Django admin (DEBUG only; for dev inspection) |
| <http://localhost:8025/> | Mailpit (intercepted outbound email) |
| <http://localhost:9001/> | MinIO console (user: `mph-dev` / pass: `mph-dev-secret`) |

**Demo tenant** (created by `seed_dev_tenant`):

| Field | Value |
| --- | --- |
| Org slug | `demo` |
| Org name | Demo Organization |
| Admin email | `admin@mph.local` |
| Admin password | `mph-demo-password!` |

These defaults can be overridden with flags:

```bash
docker compose -f backend/compose.yaml --project-directory backend exec web \
  python manage.py seed_dev_tenant \
    --slug acme --name "Acme Co" \
    --admin-email owner@acme.test \
    --admin-password 'change-me-12345'
```

To rebuild the demo tenant from scratch:

```bash
make seed-dev-reset
```

## Make targets

| Target | What it does |
| --- | --- |
| `make dev-setup` | One-command first-time setup (Linux/macOS) |
| `make build` | Build local Docker images |
| `make up` | Start the stack |
| `make down` | Stop the stack |
| `make logs` | Tail web/worker/beat logs |
| `make shell` | Django shell inside the `web` container |
| `make dbshell` | psql against local Postgres |
| `make migrate` | Apply Django migrations |
| `make makemigrations` | Generate new migrations |
| `make test` | Run the pytest suite |
| `make lint` | ruff + mypy + service-discipline (advisory) |
| `make format` | ruff format + ruff --fix |
| `make seed-dev` | Apply migrations + seed demo tenant |
| `make seed-dev-reset` | Same with `--reset` flag (drops then recreates) |
| `make check` | django-check + custom user-model baseline check |
| `make frontend-typecheck` | `tsc --noEmit` inside vite container |
| `make frontend-build` | `vite build` inside vite container |
| `make clean` | Stop and remove all volumes (DESTRUCTIVE) |

## Architecture notes (M0)

These notes capture the decisions baked into M0; full justification lives in
`docs/guide.md` and the per-milestone retrospectives in `docs/retrospectives/`.

- **Custom User model from migration #1.** `apps.platform.accounts.User` is the
  `AUTH_USER_MODEL` from day one. The repo includes a host-side static check
  (`scripts/check_user_model_baseline.py`) that fails CI if the model is ever
  removed or relocated.
- **Row-level multi-tenancy.** Every tenant-owned model in M1+ will carry an
  `organization` FK with `on_delete=PROTECT`, plus a `TenantManager`. M0
  ships the platform-tier models; the tenant scaffolding lands in M1.
- **Service-layer discipline.** State changes belong in `apps/*/services/`,
  not in models / views / signals / forms. `scripts/check_service_layer_discipline.py`
  is an advisory static check in M0; it becomes blocking at M2.
- **96 capabilities + 11 default role templates + System User** are installed
  by the `seed_v1` data migration (`apps/platform/rbac/migrations/0002_seed_v1.py`).
  Production tenant provisioning (`services.create_organization`) lands in M1;
  `seed_dev_tenant` is the dev-only equivalent that runs the same per-tenant
  clone logic inline.

## Authoritative documentation

The technical development guide is checked into `docs/guide.md`. When this
README and the guide disagree, the guide wins.
