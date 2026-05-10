"""URL bindings for health endpoints (G.4.8).

Mounted at the project root so the paths are exactly ``/healthz`` and
``/readyz``.
"""

from __future__ import annotations

from django.urls import path

from apps.common.utils import health

urlpatterns = [
    path("healthz", health.healthz, name="healthz"),
    path("readyz", health.readyz, name="readyz"),
]
