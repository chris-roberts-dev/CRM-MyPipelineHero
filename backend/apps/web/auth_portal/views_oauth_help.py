"""OAuth-failure help page (M1 D5 Phase 3).

Renders contextual copy when an OAuth/OIDC login is rejected by the
:class:`MphSocialAccountAdapter`. Each ``reason`` slug maps 1:1 to a
typed exception raised by :func:`resolve_external_user`:

* ``provider_not_active`` → :class:`ProviderNotActiveError`
* ``domain_not_allowed`` → :class:`EmailDomainNotAllowedError`
* ``email_not_verified`` → :class:`EmailNotVerifiedError`
* ``conflicting_identity`` → :class:`ConflictingExternalIdentityError`
* ``user_inactive`` → :class:`UserInactiveError`
* ``no_existing_user`` → :class:`NoExistingUserAndSelfRegistrationDisabledError`

The view validates the inbound slug against a closed allowlist; unknown
slugs render the generic ``provider_not_active`` copy (the safest
default — generic "credentials invalid" without policy leakage).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

# Closed allowlist of failure reasons. Adapter constructs these slugs;
# the view rejects anything else as if it were "provider_not_active"
# (the safest generic fallback).
_ALLOWED_REASONS: dict[str, dict[str, str]] = {
    "provider_not_active": {
        "heading": "Sign-in unavailable",
        "explanation": (
            "We weren't able to sign you in through that provider. "
            "Please try a different sign-in method, or contact support."
        ),
        "next_action_label": "Back to sign in",
    },
    "domain_not_allowed": {
        "heading": "Sign-in unavailable",
        "explanation": (
            "We weren't able to sign you in through that provider. "
            "Please try a different sign-in method, or contact support."
        ),
        "next_action_label": "Back to sign in",
    },
    "email_not_verified": {
        "heading": "Verify your email at the provider",
        "explanation": (
            "Your identity provider has not confirmed that your email "
            "address is verified. Please verify your email with the "
            "provider, then try signing in again."
        ),
        "next_action_label": "Back to sign in",
    },
    "conflicting_identity": {
        "heading": "We can't safely link this account",
        "explanation": (
            "Your account already has a different external sign-in linked "
            "for this provider. For your security, we can't automatically "
            "switch which external identity is connected to your account. "
            "Please contact support to resolve this."
        ),
        "next_action_label": "Back to sign in",
    },
    "user_inactive": {
        "heading": "No active access",
        "explanation": (
            "We found your account but it isn't currently active. "
            "Please contact your organization administrator or support."
        ),
        "next_action_label": "Back to sign in",
    },
    "no_existing_user": {
        "heading": "Invitation required",
        "explanation": (
            "You're not currently a member of any organization on "
            "MyPipelineHero. If you should have access, please ask your "
            "organization administrator to invite you."
        ),
        "next_action_label": "Back to sign in",
    },
}


@require_safe
def oauth_help(request: HttpRequest, reason: str) -> HttpResponse:
    """Render the OAuth help page for a given failure reason.

    Closed allowlist: unknown ``reason`` slugs render the generic
    ``provider_not_active`` copy (safe default).
    """
    context: dict[str, Any] = _ALLOWED_REASONS.get(
        reason, _ALLOWED_REASONS["provider_not_active"]
    )
    context = {**context, "reason": reason}
    return render(request, "auth_portal/oauth_help.html", context)
