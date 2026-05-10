"""Health check views (G.4.8).

These endpoints are intentionally unauthenticated and intentionally cheap.

* ``/healthz``     — process is alive. Returns 200 with ``{"status": "ok"}``.
* ``/readyz``      — process can serve traffic (DB + Redis reachable).
* ``/healthz/deep``— exhaustive (DB write, Redis SET, object store HEAD).

The deep check is deferred to a later milestone; this module ships ``healthz``
and ``readyz`` for M0.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import OperationalError, connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def healthz(_request: HttpRequest) -> JsonResponse:
    """Liveness probe. Always returns 200 if the process is up."""
    return JsonResponse({"status": "ok"})


@require_GET
@never_cache
def readyz(_request: HttpRequest) -> JsonResponse:
    """Readiness probe. 200 iff DB and cache are reachable; 503 otherwise."""
    checks: dict[str, Any] = {}
    overall_ok = True

    # Database round-trip
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except OperationalError as exc:
        overall_ok = False
        checks["database"] = f"error: {exc.__class__.__name__}"
    except Exception as exc:  # pragma: no cover — defensive
        overall_ok = False
        checks["database"] = f"error: {exc.__class__.__name__}"

    # Redis round-trip via Django cache
    try:
        probe_key = "__readyz__"
        cache.set(probe_key, "1", timeout=5)
        if cache.get(probe_key) != "1":
            raise RuntimeError("cache round-trip failed")
        checks["cache"] = "ok"
    except Exception as exc:
        overall_ok = False
        checks["cache"] = f"error: {exc.__class__.__name__}"

    payload = {"status": "ok" if overall_ok else "error", "checks": checks}
    return JsonResponse(payload, status=200 if overall_ok else 503)
