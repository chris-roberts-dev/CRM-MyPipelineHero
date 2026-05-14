#!/usr/bin/env bash
# MyPipelineHero — one-command first-time dev setup (I.2.4).
#
# Idempotent. Safe to re-run. Intended for Linux and macOS engineers;
# Windows engineers run the underlying `make` targets directly because
# this script can't always normalize line endings and execute reliably
# under PowerShell.
#
# What it does:
#   1. Confirms required host tooling (docker, make).
#   2. Adds `mph.local` to /etc/hosts if missing (with sudo).
#   3. Builds Docker images.
#   4. Brings the stack up.
#   5. Waits for postgres/redis/web health.
#   6. Applies migrations (creates the platform schema + seeds capabilities
#      and role templates via seed_v1).
#   7. Runs seed_dev_tenant to create the demo tenant.
#   8. Runs the pytest suite as a smoke check.
#   9. Prints the URLs and credentials for the engineer.

set -euo pipefail

REPO_ROOT="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$REPO_ROOT"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

C_GREEN="$(printf '\033[32m')"
C_YELLOW="$(printf '\033[33m')"
C_RED="$(printf '\033[31m')"
C_BOLD="$(printf '\033[1m')"
C_RESET="$(printf '\033[0m')"

step() {
    printf "\n%s==> %s%s\n" "$C_BOLD" "$1" "$C_RESET"
}

ok() {
    printf "%s ✓ %s%s\n" "$C_GREEN" "$1" "$C_RESET"
}

warn() {
    printf "%s ! %s%s\n" "$C_YELLOW" "$1" "$C_RESET"
}

die() {
    printf "%s ✗ %s%s\n" "$C_RED" "$1" "$C_RESET" >&2
    exit 1
}

# -----------------------------------------------------------------------------
# 1. Host tooling
# -----------------------------------------------------------------------------

step "Checking host tooling"

command -v docker >/dev/null 2>&1 || die "docker is not installed or not on PATH"
ok "docker present"

docker compose version >/dev/null 2>&1 || die "docker compose v2 plugin not available"
ok "docker compose v2 present"

command -v make >/dev/null 2>&1 || die "make is not installed"
ok "make present"

# -----------------------------------------------------------------------------
# 2. /etc/hosts
# -----------------------------------------------------------------------------

step "Verifying /etc/hosts entry for mph.local"

if grep -qE '^\s*127\.0\.0\.1\s+mph\.local(\s|$)' /etc/hosts; then
    ok "/etc/hosts already maps 127.0.0.1 → mph.local"
else
    warn "/etc/hosts is missing 127.0.0.1 mph.local — adding (requires sudo)"
    echo "127.0.0.1 mph.local" | sudo tee -a /etc/hosts >/dev/null
    ok "Added 127.0.0.1 mph.local"
fi

# -----------------------------------------------------------------------------
# 3-4. Build + up
# -----------------------------------------------------------------------------

step "Building Docker images"
make build
ok "Images built"

step "Starting the stack"
make up
ok "Stack started"

# -----------------------------------------------------------------------------
# 5. Wait for web
# -----------------------------------------------------------------------------

step "Waiting for the web container to become healthy"

ATTEMPTS=30
SLEEP=2
for i in $(seq 1 $ATTEMPTS); do
    if curl -sf --max-time 2 http://mph.local/healthz >/dev/null 2>&1; then
        ok "web/healthz is reachable"
        break
    fi
    if [ "$i" -eq "$ATTEMPTS" ]; then
        die "web/healthz never became reachable. Check 'make logs'."
    fi
    printf "."
    sleep $SLEEP
done

# -----------------------------------------------------------------------------
# 6-7. Migrate + seed
# -----------------------------------------------------------------------------

step "Applying migrations (includes seed_v1)"
make migrate
ok "Migrations applied"

step "Seeding demo tenant"
docker compose -f backend/compose.yaml --project-directory backend exec -T web \
    python manage.py seed_dev_tenant
ok "Demo tenant seeded"

# -----------------------------------------------------------------------------
# 8. Smoke tests
# -----------------------------------------------------------------------------

step "Running pytest smoke suite"
make test
ok "Smoke suite passed"

# -----------------------------------------------------------------------------
# 9. Final summary
# -----------------------------------------------------------------------------

cat <<EOF

${C_BOLD}MyPipelineHero local dev is ready.${C_RESET}

  Landing:        http://mph.local/
  Login (M0):     http://mph.local/login/         (scaffold; full flow in M1)
  Platform:       http://mph.local/platform/
  Django admin:   http://mph.local/django-admin/  (DEBUG only)
  Mailpit:        http://localhost:8025/
  MinIO console:  http://localhost:9001/          (user: mph-dev / pass: mph-dev-secret)

  Demo tenant credentials (seed_dev_tenant defaults):
    email:    admin@mph.local
    password: mph-demo-password!

  Useful targets:
    make logs                Tail web/worker/beat
    make test                Re-run the pytest suite
    make lint                ruff + mypy + service-discipline (advisory)
    make shell               Django shell
    make dbshell             psql
    make down                Stop the stack

EOF