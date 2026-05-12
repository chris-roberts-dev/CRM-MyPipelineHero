# MyPipelineHero

Multi-tenant CRM SaaS for organizations selling services, resale products, and
manufactured products.

This repository implements the architecture defined in
**`docs/guide.md`** (the MyPipelineHero technical development guide v0.7).
That guide is the authoritative source for architecture, terminology, domain
models, workflows, authentication, pricing, deployment, admin surfaces, and
milestone scope. Code in this repository is required to match the guide.

## Repository layout

```
frontend/        # Phase 2 React tenant-facing SPA placeholder + Phase 1 Vite assets
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
- **Node.js 20.x or 24.x on the host** (`>=20 <25` per `frontend/package.json`)

You do not need a local Python install for application work; Python runs
through containers. A local Python 3.14 install plus `pip install -r
backend/requirements/dev.txt` is supported for editor/IDE tooling.

## First-time setup

```bash
# 1. Clone the repo
git clone <repo-url> mph
cd mph

# 2. Add /etc/hosts entries for the local hostname
#    Linux/macOS:
#      sudo sh -c 'echo "127.0.0.1 mph.local" >> /etc/hosts'
#    Windows PowerShell (as Administrator):
#      Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "`n127.0.0.1 mph.local"

# 3. Install frontend dependencies on the host (one-time; ~2-3 min)
#    Uses cross-platform install so Linux container binaries are also fetched.
make frontend-install

# 4. Build images and start the stack
make build
make up

# 5. Apply migrations
make migrate

# 6. Verify
curl -sf http://mph.local/healthz
curl -sf http://mph.local/                # landing
curl -sf http://mph.local/login/          # login page (scaffold)
curl -sf http://mph.local/platform/       # platform console
curl -sf http://mph.local/vite/@vite/client > /dev/null && echo "vite OK"
open http://localhost:8025/               # Mailpit
open http://localhost:9001/               # MinIO console
```

## Why `make frontend-install` does three install passes

`node_modules/` is installed on your host (Windows/macOS/Linux native FS) and
bind-mounted into the Linux Alpine Vite container. Several frontend deps —
**Rollup**, **lightningcss**, **@tailwindcss/oxide**, **esbuild** — ship
per-platform native binaries as *optional dependencies*. A single
`npm install` only fetches binaries for the platform doing the install.

So `make frontend-install` runs the install three times:

1. **Host platform** — what `npm install` would naturally do
2. **`--os=linux --cpu=x64 --libc=musl`** — Alpine container binaries
3. **`--os=linux --cpu=x64 --libc=glibc`** — CI runner binaries

The optional binaries are small (~5-10 MB each) and dormant when not loaded.
Total `node_modules/` size impact: ~30 MB.

If you ever see `Cannot find module '@rollup/rollup-linux-x64-musl'` in
the Vite container logs, you ran a one-platform install. Re-run
`make frontend-install`.

## Updating frontend dependencies

When `frontend/package.json` changes (you pull a commit that adds/removes/bumps
a dep), re-run the host install:

```bash
make frontend-install
# Restart the vite container so it picks up the changes
docker compose -f backend/compose.yaml --project-directory backend restart vite
```

The Vite dev server itself uses HMR for code changes; only `package.json`
changes need this re-install.

## Make targets

| Target | What it does |
|---|---|
| `make build` | Build local Docker images |
| `make up` | Start the stack |
| `make down` | Stop the stack |
| `make logs` | Tail web/worker/beat logs |
| `make shell` | Django shell inside the `web` container |
| `make dbshell` | psql against local Postgres |
| `make migrate` | Apply Django migrations |
| `make makemigrations` | Generate new migrations |
| `make test` | Run the pytest suite |
| `make lint` | Run ruff + mypy + service-discipline (advisory) |
| `make format` | Run ruff format + ruff --fix |
| `make seed-dev` | Run `seed_v1` + `seed_dev_tenant` (lands in M0 D4) |
| `make check` | django-check + custom user-model baseline check |
| `make frontend-install` | Cross-platform host install (one-time / on dep changes) |
| `make frontend-install-host-only` | Quick reinstall — host platform binaries only |
| `make frontend-typecheck` | `tsc --noEmit` (on host) |
| `make frontend-build` | `vite build` (on host; produces `frontend/dist/`) |

## Authoritative documentation

The technical development guide is checked into `docs/guide.md`. When this
README and the guide disagree, the guide wins.