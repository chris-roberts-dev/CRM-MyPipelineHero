"""Tenant-subdomain URL routing (M1 D6 Phase 4A).

Mounted by ``HostUrlconfMiddleware`` when the request host matches
the tenant-subdomain template (``{slug}.mph.local``). Hosts the
tenant portal, the ``/handoff/`` consume endpoint, and tenant-
scoped resources.

Phase 4A leaves this URLconf minimal (a fallback include of
``tenant_portal.urls`` which itself is empty for now). Phase 4B
populates the real handoff consume endpoint + tenant landing.

The root-domain routes (allauth, picker) are NOT reachable from
tenant subdomains — the URL resolver only knows about routes in
this module when the host is TENANT scope.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("apps.web.tenant_portal.urls")),
]
