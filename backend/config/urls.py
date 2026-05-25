"""Default URLconf — used when HostUrlconfMiddleware doesn't pick
a per-host URLconf for the current request.

This module re-exports the root URLconf's urlpatterns so any
codepath that doesn't go through the per-host middleware (error
handlers, ``manage.py shell``, ``reverse()`` outside a request,
test cases not exercising host-aware behavior) still resolves the
landing / auth_portal / allauth routes.

Per-host routing is in :mod:`config.urls_root` and
:mod:`config.urls_tenant`; the middleware in
``apps.common.sessions.middleware.HostUrlconfMiddleware`` switches
between them based on request host.
"""

from __future__ import annotations

from config.urls_root import urlpatterns

__all__ = ["urlpatterns"]
