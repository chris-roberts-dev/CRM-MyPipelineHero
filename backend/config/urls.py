"""Project root URL configuration.

This file is intentionally thin. It composes URLs from each app's own
``urls`` module so that domain ownership stays inside the domain app
(per `docs/guide.md` § A.5.3 and § H.7.8).

Mount points (M0):

    /                    custom landing page (apps.web.landing)
    /login/              login scaffold (apps.web.auth_portal) — full flow lands in M1
    /healthz             liveness check (apps.common.utils.health)
    /readyz              readiness check (apps.common.utils.health)
    /platform/           custom platform admin shell (apps.platform.support)
    /django-admin/       dev-only raw Django admin (DEBUG only)

Mount points reserved for later milestones:

    /select-org/         org picker (M1)
    /accept-invite/      invite acceptance (M1)
    /forgot-password/    password reset (M1)
    /api/v1/             DRF internal API (Phase 2 / M9)
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin as django_admin
from django.urls import include, path

# Customize the dev-only Django admin so engineers immediately see this
# is the *raw* admin, not a product surface.
django_admin.site.site_header = "MyPipelineHero — raw model inspection (dev only)"
django_admin.site.site_title = "MyPipelineHero · Django admin"
django_admin.site.index_title = (
    "Raw model inspection. NOT a product surface. Use /platform/ for support workflows."
)


urlpatterns: list = [
    # Public landing — owned by apps.web.landing
    path("", include(("apps.web.landing.urls", "landing"), namespace="landing")),
    # Health checks (G.4.8) — unauthenticated
    path("", include("apps.common.utils.health_urls")),
    # Auth portal scaffold (M0 placeholder; full allauth wiring in M1)
    path("", include(("apps.web.auth_portal.urls", "auth_portal"), namespace="auth_portal")),
    # Custom platform admin shell (H.7.2)
    path(
        "platform/",
        include(("apps.platform.support.urls", "platform_console"), namespace="platform_console"),
    ),
]

# Dev-only raw Django admin. NEVER mounted unconditionally; never a product
# dependency (H.7.2 / J.2.4 exit criterion #10). Mounted only when DEBUG is
# True so production images cannot accidentally expose it.
if settings.DEBUG:
    urlpatterns += [
        path("django-admin/", django_admin.site.urls),
    ]
