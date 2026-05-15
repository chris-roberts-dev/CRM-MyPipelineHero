"""MFA-enforcement middleware (B.4.9 / H.3.4).

Forces local-password users without an enrolled TOTP authenticator to
complete MFA enrollment before reaching any part of the application
that requires an authenticated session.

**Why this exists outside allauth.**

Allauth.mfa ships a *challenge* middleware (intercept post-login when
the user already has an authenticator) but does NOT ship a *forced
enrollment* middleware. B.4.9 / H.3.4 require both: the user with no
authenticator is supposed to land on the enrollment screen after
login, not on the application. This middleware bridges that gap.

**What it does.**

For every authenticated request that is NOT on the allowlist:

1. Check whether the user has any TOTP authenticator. Recovery codes
   alone do not count — they are a fallback for TOTP, not a primary
   factor.
2. If yes → proceed normally (allauth.mfa's own challenge middleware
   handles the per-session challenge).
3. If no → emit ``LOCAL_MFA_CHALLENGE_REQUIRED`` (once per session)
   and 302 to ``/accounts/2fa/totp/``.

**Allowlist.**

The middleware does NOT redirect requests to:

* Allauth's account/MFA URLs (anything under ``/accounts/``) — users
  must be able to reach the enrollment form, log out, manage their
  email, etc.
* Static asset URLs (``STATIC_URL`` prefix).
* Health checks (``/healthz``, ``/readyz``).

**What it does NOT do (out of scope for M1 D4).**

* OAuth/trusted-provider-MFA carve-out — M1 D5.
* Support-impersonation carve-out — M1 D7.
* Cross-subdomain handoff awareness — M1 D6.
* Locking out users who refused enrollment and walked away
  (allauth.mfa stores enrollment as a normal authenticator row; the
  user can simply not complete enrollment, and they'll be redirected
  here on every authenticated request until they do).

**Placement in MIDDLEWARE.**

This middleware MUST run AFTER ``AuthenticationMiddleware`` (so
``request.user`` is populated) and AFTER ``SessionMiddleware`` (so
the audit-emission throttle session key works). It MAY run before or
after ``AccountMiddleware`` — order is irrelevant because allauth's
middleware doesn't redirect on the enrollment path.

**Service-layer discipline.**

This middleware performs ONE state change: setting a session key
(``_mfa_required_emitted``) to throttle audit emission to once per
session. Session writes are not ORM model writes and are exempt from
A.4.5's service-layer rule. The audit emission itself goes through
``record_auth_event``, which IS a service.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import resolve, reverse
from django.urls.exceptions import NoReverseMatch, Resolver404

logger = logging.getLogger(__name__)


# Session key used to throttle LOCAL_MFA_CHALLENGE_REQUIRED emission to
# once per session. The value is the user id at the time of emission;
# if the user changes (impersonation, reauth into a different user)
# the key is replaced.
_MFA_REQUIRED_EMITTED_KEY = "_mph_mfa_required_emitted_for"


def _has_totp_authenticator(user: Any) -> bool:
    """True if the user has at least one TOTP authenticator row.

    Recovery codes alone do NOT count — they're a fallback, not a
    primary factor. A user who has only generated recovery codes
    still needs to enroll TOTP.
    """
    # Import here to avoid app-registry-not-ready at module import time.
    from allauth.mfa.models import Authenticator

    return Authenticator.objects.filter(
        user=user,
        type=Authenticator.Type.TOTP,
    ).exists()


def _is_allowlisted_path(path: str) -> bool:
    """Allowlist for paths the middleware must never block.

    The user must be able to reach enrollment, log out, manage their
    email, view static assets, and hit health endpoints regardless of
    MFA state.
    """
    static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
    media_url = getattr(settings, "MEDIA_URL", "/media/") or "/media/"

    if path.startswith("/accounts/"):
        # Allauth's entire surface: login, logout, signup, email,
        # password reset, MFA enrollment, reauth, etc.
        return True
    if path.startswith(static_url):
        return True
    if path.startswith(media_url):
        return True
    if path in {"/healthz", "/readyz"}:
        return True
    if path.startswith("/django-admin/"):
        # Dev-only Django admin. We do NOT MFA-gate the raw admin
        # because it's only mounted when DEBUG=True and is intended
        # for offline model inspection; gating it could create a
        # chicken-and-egg if MFA tables themselves need inspection.
        # In prod this prefix is not routed, so no risk leaks.
        return True
    return False


class RequireMfaEnrollmentMiddleware:
    """Force MFA enrollment for authenticated users who don't have it.

    See module docstring for the full contract.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._should_enforce(request):
            redirect = self._enforce(request)
            if redirect is not None:
                return redirect
        return self.get_response(request)

    # ------------------------------------------------------------------

    def _should_enforce(self, request: HttpRequest) -> bool:
        """Quick gate before doing any DB work."""
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        # Defensive: System User should never authenticate, but if it
        # somehow does (bug, test fixture mistake) don't ricochet it
        # into MFA enrollment.
        if getattr(user, "is_system", False):
            return False
        if _is_allowlisted_path(request.path):
            return False
        return True

    def _enforce(self, request: HttpRequest) -> HttpResponse | None:
        """Decide whether to redirect this request to enrollment."""
        user = request.user
        if _has_totp_authenticator(user):
            return None

        # User is authenticated but has no TOTP authenticator.
        # B.4.9 → force enrollment now.
        try:
            target = reverse("mfa_activate_totp")
        except NoReverseMatch:
            # allauth.mfa not wired (shouldn't happen in M1 D4+). Fail
            # open with a logger.warning rather than 500-ing the
            # request — gating ourselves out of the entire app is
            # worse than not gating.
            logger.warning(
                "RequireMfaEnrollmentMiddleware: cannot reverse "
                "'mfa_activate_totp'; allauth.mfa is not configured. "
                "Skipping enforcement for this request."
            )
            return None

        self._emit_audit_once(request, user, target)
        return HttpResponseRedirect(target)

    def _emit_audit_once(self, request: HttpRequest, user: Any, target: str) -> None:
        """Emit LOCAL_MFA_CHALLENGE_REQUIRED at most once per session per user.

        Without this throttle, a user who refuses to enroll and keeps
        clicking around generates one audit event per request, which
        would flood the audit trail.
        """
        try:
            emitted_for = request.session.get(_MFA_REQUIRED_EMITTED_KEY)
        except AttributeError:
            # No session middleware (e.g. unit-test request with no
            # SessionMiddleware applied). Skip the throttle and emit
            # — the test environment is the only place this happens.
            emitted_for = None

        if emitted_for == str(user.id):
            return

        # Late import keeps Django startup clean.
        from apps.platform.accounts.services import record_auth_event

        record_auth_event(
            event_type="LOCAL_MFA_CHALLENGE_REQUIRED",
            actor_id=user.id,
            object_kind="platform_accounts.User",
            object_id=str(user.id),
            metadata={
                "reason": "totp_not_enrolled",
                "redirect_to": target,
                "path": request.path,
            },
        )

        try:
            request.session[_MFA_REQUIRED_EMITTED_KEY] = str(user.id)
        except AttributeError:
            pass

    def _resolve_view_name(self, request: HttpRequest) -> str | None:
        """Best-effort resolve for the requested URL's view name (for logs)."""
        try:
            return resolve(request.path).view_name
        except Resolver404:
            return None
