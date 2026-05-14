#!/bin/sh
# Vite dev-server entrypoint.
#
# This file is mounted into the vite container at /usr/local/bin/.
# The container's command in compose.yaml is `["/bin/sh", "-c", "npm
# install && npm run dev ..."]` — this entrypoint is reserved for future
# pre-flight checks (e.g. verifying frontend/package.json exists). For
# now it is a thin shell that the compose command can fall back on if
# the container is restarted manually.

set -e

echo "vite: running pre-flight checks"

if [ ! -f /app/frontend/package.json ]; then
    echo "ERROR: /app/frontend/package.json not found." >&2
    echo "Is the frontend/ directory bind-mounted into the container?" >&2
    exit 1
fi

echo "vite: pre-flight OK"
echo "vite: handing off to npm install + dev server"
exec sh -c "cd /app/frontend && npm install --no-fund --no-audit && npm run dev -- --host 0.0.0.0"