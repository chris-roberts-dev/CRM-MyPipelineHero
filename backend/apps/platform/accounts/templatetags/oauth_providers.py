"""Template tags exposing OAuth provider configuration to templates.

Used by:

* ``account/login.html`` — to render a provider button per active
  ``OAuthProviderConfig``.
* ``socialaccount/connections.html`` — to render "link this provider"
  options for providers the user hasn't linked yet.

Scoped to templates that explicitly load the tag library, rather than
a context processor that runs on every request. The login page renders
infrequently (rate-limited to ~20/hour per IP); a DB query per render
is acceptable for M1 D5 without caching.
"""

from __future__ import annotations

from typing import Any

from django import template

from apps.platform.accounts.oauth.models import OAuthProviderConfig

register = template.Library()


@register.simple_tag
def active_oauth_providers() -> list[OAuthProviderConfig]:
    """Return all OAuthProviderConfig rows with ``is_active=True``.

    Ordered by display_name (stable button order in templates).
    Returns an empty list if no providers are active — the login
    template should handle that case by simply not rendering the
    OAuth section.
    """
    return list(
        OAuthProviderConfig.objects.filter(is_active=True).order_by("display_name")
    )


@register.simple_tag
def user_linked_providers(user: Any) -> set[str]:
    """Return the set of provider_codes the user has SocialAccounts for.

    Used by ``socialaccount/connections.html`` to determine which
    providers should appear as "link this provider" buttons (i.e. the
    active providers MINUS what's already linked).

    Returns an empty set for anonymous users.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return set()

    from allauth.socialaccount.models import SocialAccount

    return set(
        SocialAccount.objects.filter(user=user).values_list("provider", flat=True)
    )
