"""Per-tenant session middleware + per-host URLconf middleware
(M1 D6 Phases 3 + 4A, B.4.14 + B.4.15).

``PerTenantSessionMiddleware`` (Phase 3) replaces Django's
standard ``SessionMiddleware`` to scope session cookies per host.

``HostUrlconfMiddleware`` (Phase 4A) sets ``request.urlconf``
based on the host scope so root-domain and tenant-subdomain URL
spaces are mutually exclusive.

**Test opt-out.** Setting ``MPH_HOST_URLCONF_ROUTING_ENABLED = False``
disables the host-routing override. Tests that need to swap in a
test-only URLconf via ``override_settings(ROOT_URLCONF=...)`` set
this flag at the class or module level. Production keeps the
default ``True`` and the middleware enforces per-host routing
normally.

**OTHER scope falls through.** When the host doesn't match root
or tenant patterns (testserver, localhost, IPs),
``HostUrlconfMiddleware`` does NOT set ``request.urlconf``.
Django then uses ``settings.ROOT_URLCONF``.

Both middlewares read the same ``request._mph_session_scope``
attribute set by ``PerTenantSessionMiddleware.process_request``.
MIDDLEWARE order MUST be: ``PerTenantSessionMiddleware`` first,
``HostUrlconfMiddleware`` second.

**Django version coupling.** ``PerTenantSessionMiddleware``
mirrors Django 5.2's ``SessionMiddleware.process_response``
closely. ``HostUrlconfMiddleware`` uses the documented
``request.urlconf`` attribute.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.conf import settings
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date

from apps.common.sessions.host_resolution import (
    HostScope,
    SessionScope,
    resolve_session_scope,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PerTenantSessionMiddleware (Phase 3 — unchanged from prior implementation).
# ---------------------------------------------------------------------------


class PerTenantSessionMiddleware(SessionMiddleware):
    """Session middleware that picks the cookie name per host."""

    def process_request(self, request: HttpRequest) -> None:
        scope = self._resolve_scope(request)
        session_key = request.COOKIES.get(scope.cookie_name)
        request.session = self.SessionStore(session_key)
        request._mph_session_scope = scope  # type: ignore[attr-defined]

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        scope: SessionScope = getattr(request, "_mph_session_scope", None) or (
            self._resolve_scope(request)
        )

        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        if scope.cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                scope.cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=scope.cookie_domain,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            patch_vary_headers(response, ("Cookie",))
        else:
            if accessed:
                patch_vary_headers(response, ("Cookie",))
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = http_date(expires_time)
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except SessionInterrupted:
                        raise
                    response.set_cookie(
                        scope.cookie_name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=scope.cookie_domain,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
        return response

    def _resolve_scope(self, request: HttpRequest) -> SessionScope:
        host = request.get_host().split(":", 1)[0]
        return resolve_session_scope(host)


# ---------------------------------------------------------------------------
# HostUrlconfMiddleware (Phase 4A).
# ---------------------------------------------------------------------------


_URLCONF_FOR_SCOPE: dict[HostScope, str] = {
    HostScope.ROOT: "config.urls_root",
    HostScope.TENANT: "config.urls_tenant",
}


class HostUrlconfMiddleware:
    """Set ``request.urlconf`` based on host scope (B.4.15).

    Root domain → ``config.urls_root``.
    Tenant subdomain → ``config.urls_tenant``.
    OTHER (testserver, localhost) → fall through to
    ``settings.ROOT_URLCONF``.

    **Test opt-out.** When
    ``settings.MPH_HOST_URLCONF_ROUTING_ENABLED = False``, the
    middleware skips the override entirely and lets
    ``settings.ROOT_URLCONF`` win. Tests that need to swap in a
    test-only URLconf (e.g. the per-host session cookie tests)
    use this flag.

    Reads ``request._mph_session_scope`` set by
    ``PerTenantSessionMiddleware.process_request``. MUST be ordered
    AFTER ``PerTenantSessionMiddleware`` in ``MIDDLEWARE``.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not getattr(settings, "MPH_HOST_URLCONF_ROUTING_ENABLED", True):
            # Tests use this to opt out and let settings.ROOT_URLCONF win.
            return self.get_response(request)

        scope: SessionScope | None = getattr(request, "_mph_session_scope", None)
        if scope is None:
            logger.warning(
                "HostUrlconfMiddleware: request._mph_session_scope is missing. "
                "Check MIDDLEWARE ordering — PerTenantSessionMiddleware must "
                "run first. Skipping URLconf override; falling through to "
                "settings.ROOT_URLCONF."
            )
        else:
            urlconf = _URLCONF_FOR_SCOPE.get(scope.host_scope)
            if urlconf is not None:
                request.urlconf = urlconf
            # OTHER scope: no override; Django uses settings.ROOT_URLCONF.
        return self.get_response(request)
