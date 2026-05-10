# MyPipelineHero

Multi-tenant CRM SaaS for organizations selling services, resale products, and
manufactured products.

<img width="1672" height="941" alt="dashboard" src="https://github.com/user-attachments/assets/fb457fd4-269b-45c5-ba39-be6541021f15" />


This repository implements the architecture defined in
**`docs/guide.md`** (the MyPipelineHero technical development guide v0.7).
That guide is the authoritative source for architecture, terminology, domain
models, workflows, authentication, pricing, deployment, admin surfaces, and
milestone scope. Code in this repository is required to match the guide.

## Repository layout

```
frontend/        # Phase 2 React tenant-facing SPA (placeholder until M9)
backend/         # Django project + apps
docs/            # Authoritative technical guide and retrospectives
scripts/         # CI / local-dev / safety scripts
```

For the canonical detailed layout see `docs/guide.md` § A.5.

## Phase posture

- **Phase 1** (M0–M8). Server-rendered Django + Tailwind + HTMX tenant portal.
  Phase 1 ships the full CRM and serves real tenants.
- **Phase 2** (M9+). React tenant portal consumes a DRF internal API. Root-domain
  landing/auth pages, custom platform admin, custom tenant admin, support
  impersonation, and email templates remain server-rendered permanently.

## Required tooling

- Docker + Docker Compose v2 (`docker compose ...`)
- GNU Make
- (optional) `dnsmasq` for wildcard `*.mph.local` DNS — see § Local subdomain DNS
  below. `/etc/hosts` is an acceptable fallback.

You do not need a local Python install; everything runs through containers.
A local Python 3.14 install plus `pip install -r backend/requirements/dev.txt`
is supported for editor/IDE tooling.

> **Python version note.** This project targets Python 3.14. The runtime image is
> `python:3.14-slim`. If a transitive dependency wheel is unavailable for
> `cp314` at the time you build, the Dockerfile installs build deps so packages
> can fall back to compiling from sdist. If you hit a hard incompatibility,
> downgrade `python:3.14-slim` → `python:3.13-slim` in
> `backend/docker/django/Dockerfile` and re-build.

## First-time setup

```bash
# 1. Clone the repo
git clone <repo-url> mph
cd mph

# 2. Create your local .env from the template
cp backend/.env.example backend/.env
# Edit backend/.env as needed — defaults work for local dev.

# 3. (Recommended) Add /etc/hosts entries for the local hostname
sudo sh -c 'echo "127.0.0.1 mph.local" >> /etc/hosts'

# 4. Build images and start the stack
make build
make up

# 5. Apply migrations
make migrate

# 6. Verify
curl -sf http://mph.local/healthz
curl -sf http://mph.local/readyz
open http://mph.local/                  # custom landing page
open http://mph.local/login/            # login page (form is scaffold-only in M0)
open http://mph.local/platform/         # custom platform admin shell
open http://mph.local/django-admin/     # raw Django admin (DEBUG only)
open http://localhost:8025/             # Mailpit
open http://localhost:9001/             # MinIO console
```

## Local subdomain DNS

Tenant subdomain routing lands in M1, but the local Nginx is already configured
for `mph.local` and `*.mph.local`.

**dnsmasq (recommended, macOS):**

```bash
brew install dnsmasq
sudo brew services start dnsmasq
sudo mkdir -p /etc/resolver
echo "nameserver 127.0.0.1" | sudo tee /etc/resolver/mph.local
```

**dnsmasq (Linux, NetworkManager):**

```bash
echo "address=/.mph.local/127.0.0.1" | sudo tee /etc/NetworkManager/dnsmasq.d/mph.conf
sudo systemctl reload NetworkManager
```

**`/etc/hosts` fallback:**

```bash
sudo sh -c 'echo "127.0.0.1 mph.local" >> /etc/hosts'
# add additional tenant slugs as you create them, e.g.:
# 127.0.0.1 acme.mph.local
```

## Make targets

| Target | What it does |
|---|---|
| `make build` | Build local Docker images |
| `make up` | Start the stack (web, worker, beat, postgres, redis, mailpit, minio, nginx) |
| `make down` | Stop the stack |
| `make logs` | Tail web/worker/beat logs |
| `make shell` | Django shell inside the `web` container |
| `make dbshell` | psql against local Postgres |
| `make migrate` | Apply Django migrations |
| `make makemigrations` | Generate new migrations |
| `make test` | Run the pytest suite |
| `make lint` | Run ruff + mypy |
| `make format` | Run ruff format + ruff --fix |
| `make seed-dev` | Run `seed_v1` + `seed_dev_tenant` (lands in next M0 deliverable) |
| `make check` | django-check + custom user-model baseline check |

## What's in this milestone

This commit is **M0 Deliverable 1: initial repository and Django foundation**.
What it ships:

- `backend/` Django project with `config/settings/{base,dev,test,staging,demo,prod}.py`
- `backend/compose.yaml` local stack (Postgres 17, Redis 7, Mailpit, MinIO, Nginx)
- `backend/docker/django/Dockerfile` Python 3.14 image
- `backend/docker/nginx/dev.conf` reverse proxy with `*.mph.local` wildcard
- Custom `platform_accounts.User` model in migration `0001_initial`
- App skeletons: `apps/platform/{accounts,organizations,rbac,audit,support}`,
  `apps/web/{landing,auth_portal,tenant_portal}`,
  `apps/common/{tenancy,outbox,services,utils,choices,tests,db,admin}`
- Custom landing page at `/`, login scaffold at `/login/`, platform-console
  shell at `/platform/`, dev-only Django admin at `/django-admin/`
- Health endpoints `/healthz`, `/readyz` (`G.4.8`)
- Celery app + worker/beat services
- pytest, ruff, mypy baseline
- `scripts/check_user_model_baseline.py`

What is **not** yet in this commit, by design (see `docs/guide.md` § J.2.3):

- Tenant subdomain routing logic (M1)
- Full authentication flows (login submission, allauth wiring, MFA) — M1
- `seed_v1` data migration body (capabilities, default roles, System User) —
  next M0 sub-deliverable, requires the rbac models to land first
- `seed_dev_tenant` command — same as above
- django-vite + Tailwind compiled-asset pipeline — next M0 sub-deliverable
- AST static-check for service-layer discipline — next M0 sub-deliverable
- Pricing engine code (M3), commercial domain code (M4)

## Authoritative documentation

The technical development guide is checked into `docs/guide.md`. Per the guide
front matter, when this README and the guide disagree, the guide wins.
