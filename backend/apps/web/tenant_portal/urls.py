"""Tenant-subdomain URL routing (M1 D6 Phase 4B).

Phase 4B populates the handoff consume endpoint and tenant landing
page.

Lives on tenant subdomains only. The host-routing middleware in
``apps.common.sessions.middleware.HostUrlconfMiddleware`` ensures
tenant requests resolve against this URLconf, never against the
root-domain ``config.urls_root``.
"""

from __future__ import annotations

from django.urls import path

from apps.web.tenant_portal.views import HandoffConsumeView, TenantLandingView

urlpatterns = [
    path("", TenantLandingView.as_view(), name="tenant_landing"),
    path("handoff/", HandoffConsumeView.as_view(), name="handoff_consume"),
]
