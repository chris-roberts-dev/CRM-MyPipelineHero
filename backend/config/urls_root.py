"""Root-domain URL routing (M1 D6 Phase 4A).

Mounted by ``HostUrlconfMiddleware`` when the request host is the
root domain (``mph.local`` in dev). Hosts the landing page, the
allauth auth surface (login / MFA / OAuth / email management), the
auth_portal (org picker, OAuth help), the health endpoints
(/healthz, /readyz), and — future — the platform admin console at
``/platform/``.

The tenant-subdomain routes (tenant portal, ``/handoff/`` consume)
live in :mod:`config.urls_tenant` and are NOT reachable from root.

OTHER-scope hosts (testserver, localhost, IPs) resolve against
``settings.ROOT_URLCONF`` which re-exports this module's
``urlpatterns``. ``HostUrlconfMiddleware`` deliberately does NOT
override ``request.urlconf`` for OTHER scope so tests that use
``override_settings(ROOT_URLCONF=...)`` continue working.

**Health URLs MUST stay at root paths** (``/healthz``, ``/readyz``).
Existing middleware allowlists and external probes depend on these
exact paths.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    # Health/readiness probes — root paths required by G.4.8 and
    # the middleware allowlist in apps.platform.accounts.middleware.
    path("", include("apps.common.utils.health_urls")),
    # Landing page.
    path("", include("apps.web.landing.urls")),
    # /login/ permanent redirect + /select-org/ + /oauth-help/.
    path("", include("apps.web.auth_portal.urls")),
    # allauth's full surface: account, mfa, socialaccount.
    path("accounts/", include("allauth.urls")),
]
