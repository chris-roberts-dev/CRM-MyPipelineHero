"""Require-MFA-enrollment middleware (M1 D4 + M1 D5 Phase 4 + M1 D6 Phase 4A).

Enforces B.4.9 enrollment requirements:

* **Local-password user without TOTP** → redirect to enrollment.
* **OAuth/OIDC user via TRUSTED provider** → bypass; provider MFA
  satisfies login MFA per B.4.8.
* **OAuth/OIDC user via UNTRUSTED provider** → redirect to enrollment;
  local step-up MFA is required.
* **Support user** → enrollment required unless the provider is
  explicitly trusted (B.3.11 + B.4.8).

**M1 D6 Phase 4A addition:** when the trusted-provider bypass
applies, also write ``mph_mfa_satisfied_at`` to session. Trusted-
provider OAuth users don't trigger allauth.mfa's ``authenticator_used``
signal (no local challenge), so without this write the picker would
have no satisfaction timestamp for OAuth-only users.

The session write is once-per-session (alongside the existing
audit-emission throttle) so the timestamp doesn't refresh on every
request and defeat the staleness check.

**Audit events emitted by this middleware:**

* ``LOCAL_MFA_CHALLENGE_REQUIRED`` — once per session.
* ``OAUTH_PROVIDER_MFA_TRUSTED`` — once per session.
* ``OAUTH_PROVIDER_MFA_NOT_TRUSTED`` — once per session.

**Why emissions go through ``record_auth_event``.** Middleware
runs outside any request-level transaction (``ATOMIC_REQUESTS=False``).
Calling ``audit_emit`` directly raises ``AuditOutsideTransactionError``.
``record_auth_event`` opens its own ``transaction.atomic()`` and
catches non-programming errors — same pattern allauth signal
handlers use.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from allauth.mfa.models import Authenticator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone

from apps.platform.accounts.oauth.models import OAuthProviderConfig
from apps.platform.accounts.services import record_auth_event
from apps.platform.accounts.signals_mfa import SESSION_KEY_MFA_SATISFIED_AT

logger = logging.getLogger(__name__)


SESSION_KEY_LOGIN_PROVIDER_CODE = "mph_login_provider_code"

SESSION_KEY_LOCAL_MFA_EMITTED = "_local_mfa_challenge_required_emitted"
SESSION_KEY_PROVIDER_MFA_TRUSTED_EMITTED = "_oauth_provider_mfa_trusted_emitted"
SESSION_KEY_PROVIDER_MFA_NOT_TRUSTED_EMITTED = "_oauth_provider_mfa_not_trusted_emitted"

MFA_ENROLLMENT_URL = "/accounts/2fa/totp/activate/"

_ALLOWLISTED_PATH_PREFIXES = (
    "/accounts/",
    "/static/",
    "/media/",
    "/healthz",
    "/readyz",
    "/oauth-help/",
)


class RequireMfaEnrollmentMiddleware:
    """Force authenticated users to enroll MFA before reaching the app."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._should_enforce(request):
            return self._enforce(request)
        return self.get_response(request)

    def _should_enforce(self, request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        if getattr(user, "is_system", False):
            return False
        if self._is_allowlisted(request.path):
            return False
        return True

    def _is_allowlisted(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in _ALLOWLISTED_PATH_PREFIXES)

    def _enforce(self, request: HttpRequest) -> HttpResponse:
        user = request.user

        if self._user_has_totp(user):
            return self.get_response(request)

        provider_code = request.session.get(SESSION_KEY_LOGIN_PROVIDER_CODE)

        if provider_code is None:
            self._emit_local_mfa_required_once(request, user_id=user.id)
            return redirect(MFA_ENROLLMENT_URL)

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
            # Trusted provider — bypass local enrollment AND record MFA
            # satisfaction. Both are once-per-session.
            self._record_provider_mfa_satisfaction_once(request)
            self._emit_provider_mfa_trusted_once(
                request,
                user_id=user.id,
                provider_code=provider_code,
            )
            return self.get_response(request)

        self._emit_provider_mfa_not_trusted_once(
            request,
            user_id=user.id,
            provider_code=provider_code,
        )
        return redirect(MFA_ENROLLMENT_URL)

    def _user_has_totp(self, user: Any) -> bool:
        return Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        ).exists()

    def _record_provider_mfa_satisfaction_once(self, request: HttpRequest) -> None:
        """Write ``mph_mfa_satisfied_at`` for trusted-provider users.

        Once-per-session to avoid refreshing the timestamp on every
        request (which would defeat downstream staleness checks).
        Only writes if the key is absent.
        """
        if SESSION_KEY_MFA_SATISFIED_AT in request.session:
            return
        request.session[SESSION_KEY_MFA_SATISFIED_AT] = timezone.now().isoformat()
        request.session.modified = True

    def _emit_local_mfa_required_once(
        self, request: HttpRequest, *, user_id: Any
    ) -> None:
        if request.session.get(SESSION_KEY_LOCAL_MFA_EMITTED):
            return
        record_auth_event(
            event_type="LOCAL_MFA_CHALLENGE_REQUIRED",
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
        if request.session.get(SESSION_KEY_PROVIDER_MFA_TRUSTED_EMITTED):
            return
        record_auth_event(
            event_type="OAUTH_PROVIDER_MFA_TRUSTED",
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
        if request.session.get(SESSION_KEY_PROVIDER_MFA_NOT_TRUSTED_EMITTED):
            return
        record_auth_event(
            event_type="OAUTH_PROVIDER_MFA_NOT_TRUSTED",
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
