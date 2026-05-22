"""PerTenantSessionMiddleware (M1 D6 Phase 3, B.4.14).

Subclasses Django's ``SessionMiddleware`` to read and write the
session cookie under a name that depends on the request host:

* Root domain → ``settings.SESSION_COOKIE_NAME`` (default
  ``"mph_root_session"``).
* Tenant subdomain → ``tenant_session_{slug}``.

Without this, a single global ``SESSION_COOKIE_NAME`` would force
either cross-domain cookie sharing (forbidden by B.4.14) or
silent collisions when the browser sees two cookies named the same
at different scopes.

**Why subclass rather than wrap.** ``SessionMiddleware`` is the
ONE place Django's session machinery reads
``settings.SESSION_COOKIE_NAME``; it does so in both
``process_request`` and ``process_response``. Wrapping with a
second middleware that pre-/post-processes those values would
require monkey-patching settings per request — fragile. Subclassing
lets us override the two methods cleanly and re-use the rest of
the session machinery (engine selection, modified-flag handling,
empty-session cleanup) unchanged.

**Django version coupling.** This implementation mirrors Django
5.2's ``SessionMiddleware.process_request`` and
``process_response`` closely. If Django changes those internals
(unlikely between 5.x point releases, possible at 6.0), this
middleware needs to be re-verified. The class doctest below
expresses the contract: anonymous-empty → no cookie set;
populated → cookie written with the host-derived name.
"""

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date

from apps.common.sessions.host_resolution import (
    SessionScope,
    resolve_session_scope,
)

logger = logging.getLogger(__name__)


class PerTenantSessionMiddleware(SessionMiddleware):
    """Session middleware that picks the cookie name per host.

    Drop-in replacement for ``django.contrib.sessions.middleware.SessionMiddleware``.
    """

    def process_request(self, request: HttpRequest) -> None:
        """Hydrate ``request.session`` from the per-host cookie."""
        scope = self._resolve_scope(request)
        session_key = request.COOKIES.get(scope.cookie_name)
        request.session = self.SessionStore(session_key)
        # Stash the scope on the request so process_response uses the
        # same classification (avoids re-parsing the host twice).
        request._mph_session_scope = scope  # type: ignore[attr-defined]

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """Write the per-host cookie back to the response.

        Mirror of Django 5.2's SessionMiddleware.process_response,
        with the cookie name and domain derived from
        ``request._mph_session_scope`` instead of settings.
        """
        # In rare cases (e.g. an exception before process_request set
        # the attribute), re-resolve from scratch. Defensive.
        scope: SessionScope = getattr(request, "_mph_session_scope", None) or (
            self._resolve_scope(request)
        )

        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            # request.session might be unset (e.g. during 500 handler).
            return response

        # First check if we need to delete this cookie. The session
        # has been emptied if empty=True, so delete the cookie.
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
                # Save the session data and refresh the client cookie.
                # Skip session save for 5xx responses.
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except SessionInterrupted:
                        # The session was deleted from the DB between the
                        # initial read and now. Re-raise so the user gets
                        # a clear failure rather than a silent empty session.
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

    # ------------------------------------------------------------------
    # Helpers.
    # ------------------------------------------------------------------

    def _resolve_scope(self, request: HttpRequest) -> SessionScope:
        """Compute the SessionScope for this request, stripping port."""
        # request.get_host() includes the port; strip it for matching.
        host = request.get_host().split(":", 1)[0]
        return resolve_session_scope(host)
