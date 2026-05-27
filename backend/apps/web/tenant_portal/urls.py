"""Tenant-subdomain URL routing (M1 D6 Phase 4B + Phase 5, M1 D7 Phase 5)."""

from __future__ import annotations

from django.urls import path

from apps.web.tenant_portal.views import (
    EndImpersonationFromTenantView,
    HandoffConsumeView,
    TenantLandingView,
    TenantLogoutView,
)

urlpatterns = [
    path("", TenantLandingView.as_view(), name="tenant_landing"),
    path("handoff/", HandoffConsumeView.as_view(), name="handoff_consume"),
    path("logout/", TenantLogoutView.as_view(), name="tenant_logout"),
    # M1 D7 Phase 5 — End impersonation from the tenant banner.
    path(
        "end-impersonation/",
        EndImpersonationFromTenantView.as_view(),
        name="tenant_end_impersonation",
    ),
]
