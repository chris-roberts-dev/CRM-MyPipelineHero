"""MPH social-account adapter for django-allauth (M1 D5 Phase 3).

This adapter is the HTTP boundary between allauth's OAuth/OIDC flow
and our :func:`resolve_external_user` service. Allauth invokes
``pre_social_login`` once a provider callback has validated cryptographically
(state, nonce, ID token signature, issuer, audience, expiry per B.4.5) and
before allauth proceeds to associate the social account with a User row.

Our override does the following inside ``pre_social_login``:

1. Build :class:`ExternalIdentityClaims` from the inbound
   ``SocialLogin`` via :func:`normalize_socialaccount_claims`.
2. Load the matching :class:`OAuthProviderConfig` row.
3. Call :func:`resolve_external_user` to enforce B.4.6 / B.4.7
   linking policy and return the canonical User.
4. On success: mutate ``sociallogin.user`` to point at the resolved
   User so allauth proceeds with that user.
5. On a typed exception: emit ``OAUTH_LOGIN_FAILED`` with a
   ``failure_reason`` metadata, then raise
   :class:`ImmediateHttpResponse` redirecting to the help page.

**Why ImmediateHttpResponse and not return None.** Returning None
tells allauth "no objection, proceed." Raising ImmediateHttpResponse
is the documented way to halt the flow and force a redirect from
inside the adapter callback.

**Cached System User actor id.** The service requires an actor_id.
At pre_social_login time no user is authenticated (that's the entire
point of this hook firing before authentication). We use the System
User per B.3.10. The id is cached on the adapter class after first
lookup to avoid a DB hit per OAuth callback.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar
from uuid import UUID

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.platform.accounts.oauth.claims import (
    normalize_socialaccount_claims,
)
from apps.platform.accounts.oauth.models import OAuthProviderConfig
from apps.platform.accounts.services import (
    ConflictingExternalIdentityError,
    EmailDomainNotAllowedError,
    EmailNotVerifiedError,
    NoExistingUserAndSelfRegistrationDisabledError,
    ProviderNotActiveError,
    UserInactiveError,
    resolve_external_user,
)
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


# Mapping from typed exception → URL slug for /oauth-help/<slug>/.
# Each slug is also the value used in the OAUTH_LOGIN_FAILED audit
# event's ``failure_reason`` metadata, so the audit catalog is
# consistent with user-facing exit points.
_EXCEPTION_TO_FAILURE_REASON: dict[type[Exception], str] = {
    ProviderNotActiveError: "provider_not_active",
    EmailDomainNotAllowedError: "domain_not_allowed",
    EmailNotVerifiedError: "email_not_verified",
    ConflictingExternalIdentityError: "conflicting_identity",
    UserInactiveError: "user_inactive",
    NoExistingUserAndSelfRegistrationDisabledError: "no_existing_user",
}


class MphSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Allauth socialaccount adapter implementing MPH policy.

    Configured via the ``SOCIALACCOUNT_ADAPTER`` setting in base.py.
    """

    # Lazily-populated cache of the System User id. Populated by
    # ``_get_system_actor_id`` on first access. Class-level cache is
    # safe because the System User row is immutable per B.3.10.
    _system_actor_id: ClassVar[UUID | None] = None

    @classmethod
    def _get_system_actor_id(cls) -> UUID:
        """Return the System User id, caching after first lookup.

        Raises:
            User.DoesNotExist: if no System User exists. This indicates
            the seed migration didn't run; the OAuth callback cannot
            proceed safely without a system actor.
        """
        if cls._system_actor_id is None:
            UserModel = get_user_model()
            cls._system_actor_id = UserModel.objects.get(is_system=True).id
        return cls._system_actor_id

    @classmethod
    def _reset_system_actor_id_cache(cls) -> None:
        """Test helper: clear the cached System User id.

        Tests that re-seed the DB or test the cache-miss path can
        invoke this to force a fresh lookup. Never called in
        production code.
        """
        cls._system_actor_id = None

    def pre_social_login(
        self,
        request: HttpRequest,
        sociallogin: Any,
    ) -> None:
        """Enforce B.4.6 / B.4.7 linking policy via resolve_external_user.

        Args:
            request: The HTTP request mid-callback.
            sociallogin: Allauth's SocialLogin instance. Has ``.account``
                (SocialAccount with provider/uid/extra_data) and
                ``.user`` (in-flight User, possibly unsaved).

        Side effects:
            * Emits ``OAUTH_LOGIN_STARTED`` (every call).
            * Emits ``OAUTH_LOGIN_FAILED`` on typed exception.
            * On success, swaps ``sociallogin.user`` to the resolved
              canonical User. Allauth then proceeds with login on
              that user.

        Raises:
            ImmediateHttpResponse: on any typed exception, to halt
                allauth and redirect to the help page.
        """
        claims = normalize_socialaccount_claims(sociallogin)
        actor_id = self._get_system_actor_id()

        # OAUTH_LOGIN_STARTED — emit before the policy decision so we
        # log every callback attempt. Failure events follow if the
        # decision rejects.
        audit_emit(
            "OAUTH_LOGIN_STARTED",
            actor_id=actor_id,
            organization_id=None,
            object_kind=None,
            object_id=None,
            metadata={
                "provider_code": claims.provider_code,
                "email_present": claims.email is not None,
                "email_verified": claims.email_verified,
            },
        )

        # Load the provider config matching the inbound claim.
        try:
            provider_config = OAuthProviderConfig.objects.get(
                provider_code=claims.provider_code,
            )
        except OAuthProviderConfig.DoesNotExist:
            # An OAuth callback arrived for a provider we have no
            # config for. This shouldn't happen with our loader
            # (which only registers configured providers), but if it
            # does, treat it as a deactivated provider for failure
            # categorization.
            logger.warning(
                "OAuth callback for unknown provider_code=%r; rejecting.",
                claims.provider_code,
            )
            self._emit_failure(
                actor_id=actor_id,
                provider_code=claims.provider_code,
                failure_reason="provider_not_active",
            )
            raise ImmediateHttpResponse(
                self._render_help_redirect("provider_not_active")
            )

        # Run the resolution service. Each typed exception maps to a
        # specific failure_reason / help-page redirect.
        try:
            resolved_user = resolve_external_user(
                claims=claims,
                provider_config=provider_config,
                actor_id=actor_id,
            )
        except tuple(_EXCEPTION_TO_FAILURE_REASON) as exc:
            failure_reason = _EXCEPTION_TO_FAILURE_REASON[type(exc)]
            self._emit_failure(
                actor_id=actor_id,
                provider_code=claims.provider_code,
                failure_reason=failure_reason,
            )
            logger.info(
                "OAuth login rejected: provider=%s reason=%s",
                claims.provider_code,
                failure_reason,
            )
            raise ImmediateHttpResponse(
                self._render_help_redirect(failure_reason)
            ) from exc

        # Success: tell allauth to use our resolved canonical user.
        # Allauth will then run its login mechanics (session creation,
        # `user_logged_in` signal, etc.) against this user.
        sociallogin.user = resolved_user

    def _emit_failure(
        self,
        *,
        actor_id: UUID,
        provider_code: str,
        failure_reason: str,
    ) -> None:
        """Emit OAUTH_LOGIN_FAILED with the structured failure reason.

        The reason value is from the closed set in
        ``_EXCEPTION_TO_FAILURE_REASON``, so the audit catalog stays
        consistent and queryable.
        """
        audit_emit(
            "OAUTH_LOGIN_FAILED",
            actor_id=actor_id,
            organization_id=None,
            object_kind=None,
            object_id=None,
            metadata={
                "provider_code": provider_code,
                "failure_reason": failure_reason,
            },
        )

    def _render_help_redirect(self, failure_reason: str) -> HttpResponse:
        """Redirect to the OAuth help page for a given failure reason.

        The help-page view (apps.web.auth_portal.views_oauth_help)
        validates the slug against an allowlist before rendering.
        """
        url = reverse("auth_portal:oauth_help", kwargs={"reason": failure_reason})
        return redirect(url)
