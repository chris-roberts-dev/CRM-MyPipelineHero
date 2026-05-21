"""OAuth/OIDC integration for the accounts app (M1 D5).

Houses:

* :class:`OAuthProviderConfig` — platform-managed configuration row
  for each approved OAuth/OIDC provider (B.3.7).
* :class:`ExternalIdentityClaims` — normalized, immutable shape that
  the rest of the auth code consumes (B.3.8). Raw provider claims
  MUST NOT be passed to business logic.
* :func:`normalize_socialaccount_claims` — translates allauth's
  ``SocialLogin`` into our normalized shape.
* :func:`load_socialaccount_providers` — at startup, reads active
  ``OAuthProviderConfig`` rows and produces the
  ``SOCIALACCOUNT_PROVIDERS`` dict allauth expects.

The :func:`resolve_external_user` service (B.4.6) lives in the
``services`` package alongside ``register_local_user`` and
``record_auth_event``; it lands in Phase 2.
"""

from __future__ import annotations

from apps.platform.accounts.oauth.claims import (
    ExternalIdentityClaims,
    normalize_socialaccount_claims,
)
from apps.platform.accounts.oauth.loader import load_socialaccount_providers
from apps.platform.accounts.oauth.models import (
    OAuthProviderConfig,
    ProviderType,
)

__all__ = [
    "ExternalIdentityClaims",
    "OAuthProviderConfig",
    "ProviderType",
    "load_socialaccount_providers",
    "normalize_socialaccount_claims",
]
