"""Require-MFA-enrollment middleware (M1 D4 + M1 D5 Phase 4).

Enforces B.4.9 enrollment requirements:

* **Local-password user without TOTP** → redirect to enrollment.
* **OAuth/OIDC user via TRUSTED provider** → bypass; provider MFA
  satisfies login MFA per B.4.8.
* **OAuth/OIDC user via UNTRUSTED provider** → redirect to enrollment;
  local step-up MFA is required.
* **Support user** → enrollment required unless the provider is
  explicitly trusted (B.3.11 + B.4.8).

The middleware reads the current login's provider code from a session
key (``mph_login_provider_code``) that is written by the
``social_account_login`` signal handler at OAuth login time. Local-
password logins leave the session key absent.

**What this middleware does NOT do.** It does not bypass the
*TOTP challenge* for trusted-provider users — only the *enrollment*
requirement. Allauth.mfa's challenge middleware fires the challenge
on every login regardless of method. Trusted-provider challenge
bypass is deferred to a future deliverable; the conservative
fallback (extra MFA challenge) is safe.

**Audit events emitted by this middleware:**

* ``LOCAL_MFA_CHALLENGE_REQUIRED`` — once per session, when a local-
  password user without TOTP is forced to enrollment.
* ``OAUTH_PROVIDER_MFA_TRUSTED`` — once per session, when a trusted-
  provider OAuth user bypasses local enrollment.
* ``OAUTH_PROVIDER_MFA_NOT_TRUSTED`` — once per session, when an
  untrusted-provider OAuth user is forced to local enrollment.

The once-per-session throttle uses session-key flags so log lines
don't accumulate one row per page view.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from allauth.mfa.models import Authenticator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from apps.platform.accounts.oauth.models import OAuthProviderConfig
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


# Session key written by the OAuth signal handler at login time.
# Holds the provider_code (string) of the OAuthProviderConfig that
# authenticated the user. Absent for local-password logins.
SESSION_KEY_LOGIN_PROVIDER_CODE = "mph_login_provider_code"

# Session key marking "we already emitted LOCAL_MFA_CHALLENGE_REQUIRED
# for this session" — once-per-session throttle (M1 D4).
SESSION_KEY_LOCAL_MFA_EMITTED = "_local_mfa_challenge_required_emitted"

# Session keys marking "we already emitted the trusted/untrusted
# provider audit event for this session" (M1 D5 Phase 4).
SESSION_KEY_PROVIDER_MFA_TRUSTED_EMITTED = "_oauth_provider_mfa_trusted_emitted"
SESSION_KEY_PROVIDER_MFA_NOT_TRUSTED_EMITTED = "_oauth_provider_mfa_not_trusted_emitted"

# URL the middleware redirects to when forcing enrollment. Reverse
# would be cleaner but reversing every request adds overhead; the
# allauth.mfa URL is stable across allauth versions in M1's
# supported range.
MFA_ENROLLMENT_URL = "/accounts/2fa/totp/activate/"

# Paths the middleware MUST NOT redirect from — even for an
# unenrolled user. Allowing the user to reach the enrollment URL
# itself, the logout URL, account settings, static assets, and
# health endpoints is essential to avoid lockout.
#
# All paths are prefix-matched (startswith).
_ALLOWLISTED_PATH_PREFIXES = (
    "/accounts/",  # allauth's entire surface — enrollment, logout, etc.
    "/static/",
    "/media/",
    "/healthz",
    "/readyz",
    "/oauth-help/",  # M1 D5 Phase 3 — must be reachable from any state
)


class RequireMfaEnrollmentMiddleware:
    """Force authenticated users to enroll MFA before reaching the app.

    See module docstring for the full enforcement matrix.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._should_enforce(request):
            return self._enforce(request)
        return self.get_response(request)

    # ------------------------------------------------------------------
    # Enforcement decision.
    # ------------------------------------------------------------------

    def _should_enforce(self, request: HttpRequest) -> bool:
        """True iff this request needs the enrollment gate."""
        # Anonymous users have nothing to enroll.
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False

        # System User is a service identity (per B.3.10) — should
        # never reach a UI surface, but defend in depth.
        if getattr(user, "is_system", False):
            return False

        # Allowlisted paths must always pass through.
        if self._is_allowlisted(request.path):
            return False

        return True

    def _is_allowlisted(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in _ALLOWLISTED_PATH_PREFIXES)

    # ------------------------------------------------------------------
    # Enforcement action.
    # ------------------------------------------------------------------

    def _enforce(self, request: HttpRequest) -> HttpResponse:
        """Decide whether to redirect to enrollment based on user state."""
        user = request.user

        # Does the user already have TOTP enrolled? If so, no action
        # needed regardless of login method — they satisfy MFA.
        if self._user_has_totp(user):
            return self.get_response(request)

        # The user has no TOTP. Decide based on login method.
        provider_code = request.session.get(SESSION_KEY_LOGIN_PROVIDER_CODE)

        if provider_code is None:
            # Local-password login (no provider code on session). Force
            # enrollment — M1 D4 behavior preserved.
            self._emit_local_mfa_required_once(request, user_id=user.id)
            return redirect(MFA_ENROLLMENT_URL)

        # OAuth/OIDC login. Check whether the provider is trusted for
        # MFA. If we can't resolve the provider (deleted / deactivated
        # between login and now), fall back to forcing enrollment —
        # the safe default per B.4.8.
        try:
            provider_config = OAuthProviderConfig.objects.get(
                provider_code=provider_code,
            )
        except OAuthProviderConfig.DoesNotExist:
            logger.warning(
                "User %s has session.mph_login_provider_code=%r but no "
                "matching OAuthProviderConfig. Forcing local MFA enrollment.",
                user.id,
                provider_code,
            )
            self._emit_provider_mfa_not_trusted_once(
                request,
                user_id=user.id,
                provider_code=provider_code,
            )
            return redirect(MFA_ENROLLMENT_URL)

        if provider_config.trust_external_mfa:
            # Trusted provider — bypass local enrollment. B.4.8: provider
            # MFA satisfies login MFA.
            self._emit_provider_mfa_trusted_once(
                request,
                user_id=user.id,
                provider_code=provider_code,
            )
            return self.get_response(request)

        # Untrusted provider — local step-up MFA required.
        self._emit_provider_mfa_not_trusted_once(
            request,
            user_id=user.id,
            provider_code=provider_code,
        )
        return redirect(MFA_ENROLLMENT_URL)

    # ------------------------------------------------------------------
    # Helpers.
    # ------------------------------------------------------------------

    def _user_has_totp(self, user: Any) -> bool:
        """True iff the user has at least one TOTP Authenticator row."""
        return Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        ).exists()

    def _emit_local_mfa_required_once(
        self, request: HttpRequest, *, user_id: Any
    ) -> None:
        """Emit LOCAL_MFA_CHALLENGE_REQUIRED at most once per session."""
        if request.session.get(SESSION_KEY_LOCAL_MFA_EMITTED):
            return

        audit_emit(
            "LOCAL_MFA_CHALLENGE_REQUIRED",
            actor_id=user_id,
            organization_id=None,
            object_kind="platform_accounts.User",
            object_id=str(user_id),
            metadata={
                "reason": "totp_not_enrolled",
                "redirect_to": MFA_ENROLLMENT_URL,
                "path": request.path,
            },
        )
        request.session[SESSION_KEY_LOCAL_MFA_EMITTED] = True

    def _emit_provider_mfa_trusted_once(
        self,
        request: HttpRequest,
        *,
        user_id: Any,
        provider_code: str,
    ) -> None:
        """Emit OAUTH_PROVIDER_MFA_TRUSTED at most once per session."""
        if request.session.get(SESSION_KEY_PROVIDER_MFA_TRUSTED_EMITTED):
            return

        audit_emit(
            "OAUTH_PROVIDER_MFA_TRUSTED",
            actor_id=user_id,
            organization_id=None,
            object_kind="platform_accounts.User",
            object_id=str(user_id),
            metadata={
                "provider_code": provider_code,
                "decision": "bypass_local_enrollment",
            },
        )
        request.session[SESSION_KEY_PROVIDER_MFA_TRUSTED_EMITTED] = True

    def _emit_provider_mfa_not_trusted_once(
        self,
        request: HttpRequest,
        *,
        user_id: Any,
        provider_code: str,
    ) -> None:
        """Emit OAUTH_PROVIDER_MFA_NOT_TRUSTED at most once per session."""
        if request.session.get(SESSION_KEY_PROVIDER_MFA_NOT_TRUSTED_EMITTED):
            return

        audit_emit(
            "OAUTH_PROVIDER_MFA_NOT_TRUSTED",
            actor_id=user_id,
            organization_id=None,
            object_kind="platform_accounts.User",
            object_id=str(user_id),
            metadata={
                "provider_code": provider_code,
                "decision": "force_local_enrollment",
                "redirect_to": MFA_ENROLLMENT_URL,
            },
        )
        request.session[SESSION_KEY_PROVIDER_MFA_NOT_TRUSTED_EMITTED] = True
