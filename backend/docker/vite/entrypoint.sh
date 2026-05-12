#!/bin/sh
# Vite dev-server entrypoint.
#
# Refuses to start if frontend/node_modules is missing or empty. This
# project uses the host-install pattern for node_modules (see README §
# "Why host-install Node") because installing inside the container on
# Windows + WSL2 is dramatically slower than installing on the host's
# native filesystem.
#
# Sanity-checks that the Linux x64 musl native binaries for Rollup are
# present — they get pulled in by `make frontend-install` which performs
# a cross-platform install. If you ran `cd frontend && npm install`
# directly, Rollup's Linux binary won't be there and Vite startup will
# crash with: "Cannot find module '@rollup/rollup-linux-x64-musl'".
#
# Engineer's recovery action:
#   make frontend-install

set -e

if [ ! -d node_modules ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
    echo "ERROR: frontend/node_modules is empty." >&2
    echo "Run on the host first:  make frontend-install" >&2
    exit 1
fi

if [ ! -d node_modules/@rollup/rollup-linux-x64-musl ]; then
    echo "ERROR: missing @rollup/rollup-linux-x64-musl in node_modules." >&2
    echo "" >&2
    echo "Your node_modules was installed without Linux Alpine binaries." >&2
    echo "Vite cannot start inside this container without them." >&2
    echo "" >&2
    echo "Run on the host:" >&2
    echo "  make frontend-install" >&2
    echo "" >&2
    echo "This re-installs with --os=linux --cpu=x64 --libc=musl flags" >&2
    echo "that pull the Alpine-compatible native binaries." >&2
    exit 1
fi

echo "vite: starting dev server"
exec npm run dev -- --host 0.0.0.0