"""Normalized external-identity claims (B.3.8).

Provider claims arrive from allauth in a variety of provider-specific
shapes. The application MUST normalize them into a small internal
shape before account resolution (B.3.8). This module owns that shape
and the translator.

**Why normalize.** B.3.8 is explicit: "Raw provider claims MUST NOT be
used directly in authorization decisions." If business logic reads
``sociallogin.account.extra_data["email"]`` directly, it's coupled to
the provider's claim layout. Normalization moves that coupling into
one place (this module) where it can be tested, audited, and changed
without rippling.

**What's safe to put in raw_claims.** The raw_claims dict is retained
so service code can introspect provider-specific fields when
necessary (e.g. for support debugging). However, raw_claims MUST NOT
contain tokens, authorization codes, refresh tokens, ID tokens, or
client secrets. Allauth's ``SocialLogin.account.extra_data`` already
excludes tokens by default, so we copy it as-is.

**What's NOT in this dataclass.** No access tokens, no refresh
tokens, no ID tokens. Per B.5.6 #6: "Provider tokens MUST NOT be
stored unless explicitly required." We don't store them. Allauth's
``SocialToken`` may persist them in some configurations, but our
normalized claims object never carries them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExternalIdentityClaims:
    """B.3.8 normalized claims shape.

    All fields are read-only after construction. The raw_claims dict
    is shallow-copied at construction time so callers can't mutate it
    via reference.

    NOTE: B.3.8 specifies `raw_claims: Mapping[str, Any]`. We use
    `dict[str, Any]` so the copy-on-construct semantics are explicit;
    the read-only contract is preserved by the dataclass freeze.
    """

    provider_code: str
    """The OAuthProviderConfig.provider_code that produced these claims."""

    provider_uid: str
    """Stable subject identifier from the provider. B.3.6: preferred over email."""

    email: str | None
    """Normalized lowercase email address. May be None if provider didn't return one."""

    email_verified: bool
    """Did the provider assert email verification? B.5.6: required for linking."""

    display_name: str | None
    """Optional display name from provider (e.g. OIDC `name` claim)."""

    raw_claims: dict[str, Any] = field(default_factory=dict)
    """Provider claim dict, minus tokens. Read-only by contract."""

    acr: str | None = None
    """OIDC `acr` claim — authentication context class reference."""

    amr: tuple[str, ...] = ()
    """OIDC `amr` claim — authentication methods reference (e.g. ('mfa',))."""

    def __post_init__(self) -> None:
        # Freeze the raw_claims dict by replacing it with a copy. This
        # makes the immutability story honest: the dataclass is frozen,
        # but a mutable dict field would still allow `claims.raw_claims["foo"] = "bar"`.
        # We use object.__setattr__ because the dataclass is frozen.
        object.__setattr__(self, "raw_claims", dict(self.raw_claims))
        # Normalize email to lowercase if present (defense in depth).
        if self.email is not None:
            object.__setattr__(self, "email", self.email.lower().strip())


def _coerce_amr(value: Any) -> tuple[str, ...]:
    """Normalize provider AMR to a tuple of strings."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    return ()


def _coerce_email_verified(extra_data: dict[str, Any]) -> bool:
    """Extract email_verified across provider variations.

    OIDC standard: ``email_verified`` boolean.
    Google: ``email_verified`` boolean (compliant).
    Microsoft (Azure AD): no ``email_verified``; trust ``email`` from
    ``upn``/``preferred_username`` if present.
    GitHub: ``email`` is verified iff returned by the verified-emails
    endpoint, but allauth's GitHub adapter doesn't always surface it.

    Default policy: ``email_verified`` claim is the source of truth.
    If absent, treat as False. Providers we explicitly trust to skip
    this check declare so via ``OAuthProviderConfig.require_verified_email``
    — but the *claim* itself stays False here; the policy decision
    happens in :func:`resolve_external_user` (Phase 2).
    """
    return bool(extra_data.get("email_verified", False))


def normalize_socialaccount_claims(sociallogin: Any) -> ExternalIdentityClaims:
    """Translate an allauth ``SocialLogin`` into our normalized shape.

    Called by the social-account adapter's ``pre_social_login`` hook
    (Phase 3). Returns an immutable, business-logic-safe view.

    Args:
        sociallogin: allauth's ``SocialLogin`` instance. Has
            ``.account`` (the ``SocialAccount``) and ``.user`` (the
            in-flight ``User``, possibly unsaved). We read claims
            from ``account.extra_data`` and the account's ``provider``
            and ``uid``.

    Returns:
        :class:`ExternalIdentityClaims` with provider_code, provider_uid,
        normalized email, email_verified, optional display_name, acr/amr
        if present, and a sanitized raw_claims copy.
    """
    account = sociallogin.account
    extra_data: dict[str, Any] = dict(getattr(account, "extra_data", {}) or {})

    # Strip token-like keys defensively. Allauth's extra_data shouldn't
    # contain tokens, but normalization is a single chokepoint where we
    # enforce the no-tokens-in-claims rule.
    for sensitive_key in (
        "access_token",
        "refresh_token",
        "id_token",
        "code",
        "client_secret",
        "private_key",
    ):
        extra_data.pop(sensitive_key, None)

    email_raw = extra_data.get("email")
    email = email_raw.lower().strip() if isinstance(email_raw, str) else None

    return ExternalIdentityClaims(
        provider_code=str(account.provider),
        provider_uid=str(account.uid),
        email=email,
        email_verified=_coerce_email_verified(extra_data),
        display_name=extra_data.get("name") or extra_data.get("display_name"),
        raw_claims=extra_data,
        acr=extra_data.get("acr"),
        amr=_coerce_amr(extra_data.get("amr")),
    )
