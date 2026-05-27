"""Tenant-portal middleware (M1 D7 Phase 5).

:class:`EnforceImpersonationLiveness` — when a tenant session is an
impersonation session (has ``mph_session_impersonator_admin_id`` set
to a non-None value), check that the underlying
``ImpersonationSession`` row is still active. If the row has been
ended (e.g. by the admin from the platform console), force tenant
logout immediately.

**Why a middleware and not a view decorator?** Tenant views will
multiply rapidly in M2+. Putting the check at the middleware layer
guarantees it fires for EVERY tenant request without each view
having to opt in.

**Performance.** The check is a single SELECT, and only runs when
the session indicates impersonation. Non-impersonation sessions
short-circuit on the cheap session-key read.

**Placement.** Registered in the global ``MIDDLEWARE`` list. It
self-guards via the session key — root-domain requests don't have
the impersonator session key set, so the middleware is a no-op for
those. (More precisely: ``request.session.get`` may not be
available on every code path, so we check ``hasattr`` first.)

The middleware runs AFTER ``AuthenticationMiddleware`` so
``request.user`` is populated. It runs AFTER
``HostUrlconfMiddleware`` so the urlconf is settled (though we don't
read it here).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

from apps.platform.accounts.handoff.services import (
    SESSION_KEY_IMPERSONATOR_ADMIN_ID,
)
from apps.platform.accounts.impersonation.models import ImpersonationSession

logger = logging.getLogger(__name__)


def _root_domain_url(request: HttpRequest, path: str) -> str:
    scheme = "https" if request.is_secure() else "http"
    return f"{scheme}://{settings.MPH_ROOT_DOMAIN}{path}"


class EnforceImpersonationLiveness:
    """Force logout when an impersonation session has been ended.

    Reads the session key ``mph_session_impersonator_admin_id``.
    If set to a non-None UUID string:
      1. Look up the matching active ImpersonationSession by
         (admin_user_id=impersonator, target_user_id=request.user.id,
         ended_at IS NULL).
      2. If no active session found → the admin (or someone) ended
         it. Force tenant logout, redirect to root.
      3. If found → request proceeds normally.

    The lookup is by (admin, target, active) rather than by session
    UUID because we'd need to plumb the ImpersonationSession.id
    through the handoff to recover it here. The (admin, target,
    active) combination is unique by the partial unique index
    (one active per admin) + the natural shape of the use case.

    Actually — even simpler: the partial unique index guarantees at
    most one active session per admin. We just query
    ``ImpersonationSession.objects.active_for_admin(impersonator_id)``
    and check that the row's ``target_user_id`` matches
    ``request.user.id``. If not, something is wrong and we force
    logout defensively.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Cheap path: short-circuit when there's no session, no
        # authenticated user, or no impersonation key.
        if not hasattr(request, "session"):
            return self.get_response(request)
        if not getattr(request.user, "is_authenticated", False):
            return self.get_response(request)

        impersonator_raw = request.session.get(SESSION_KEY_IMPERSONATOR_ADMIN_ID)
        if impersonator_raw is None:
            return self.get_response(request)

        # We have an impersonation session in the cookie. Check the
        # database for liveness.
        try:
            impersonator_id = UUID(impersonator_raw)
        except (TypeError, ValueError):
            logger.warning(
                "EnforceImpersonationLiveness: malformed "
                "impersonator session key %r; forcing logout.",
                impersonator_raw,
            )
            return self._force_logout(request)

        active_session = ImpersonationSession.objects.active_for_admin(impersonator_id)
        if active_session is None:
            logger.info(
                "EnforceImpersonationLiveness: no active "
                "ImpersonationSession for admin %s; forcing tenant "
                "logout for user %s.",
                impersonator_id,
                request.user.id,
            )
            return self._force_logout(request)

        # Defensive: confirm the active session's target matches the
        # currently-authenticated user. A mismatch would mean
        # something has gone wrong; safest action is to log out.
        if active_session.target_user_id != request.user.id:
            logger.warning(
                "EnforceImpersonationLiveness: active session target "
                "%s does not match request user %s; forcing logout.",
                active_session.target_user_id,
                request.user.id,
            )
            return self._force_logout(request)

        return self.get_response(request)

    def _force_logout(self, request: HttpRequest) -> HttpResponse:
        """Flush the tenant session and redirect to root."""
        django_logout(request)
        return HttpResponseRedirect(_root_domain_url(request, "/select-org/"))
