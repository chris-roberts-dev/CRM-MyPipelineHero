"""Typed exceptions for the accounts service layer.

Pattern mirrors :mod:`apps.platform.organizations.services.exceptions`:

* ``LookupError`` subclasses for missing records.
* ``ValueError`` subclasses for business-rule violations.

These are part of the public service contract — caller code branches
on them.
"""

from __future__ import annotations

from uuid import UUID

# ---------------------------------------------------------------------------
# M1 D4 — local account exceptions.
# ---------------------------------------------------------------------------


class UserNotFoundError(LookupError):
    """Raised when a service references a User id that does not exist."""

    def __init__(self, user_id: UUID | str) -> None:
        super().__init__(f"User with id {user_id!r} does not exist.")
        self.user_id = user_id


class UserAlreadyExistsError(ValueError):
    """Raised when registering a local user with an email that already exists.

    The collision is detected before any DB write; the caller can branch
    cleanly between "send password reset" vs. "first-time registration".
    """

    def __init__(self, email: str) -> None:
        super().__init__(f"A user with email {email!r} already exists.")
        self.email = email


# ---------------------------------------------------------------------------
# M1 D5 — OAuth/OIDC resolution exceptions (B.4.5, B.4.6, B.4.7).
# ---------------------------------------------------------------------------


class UserInactiveError(LookupError):
    """Raised when the resolved User has ``is_active=False``.

    The login MUST stop and the user MUST NOT be authenticated. The
    adapter (Phase 3) maps this to the same "no active access" exit
    as the no-existing-user case.
    """

    def __init__(self, user_id: UUID | str | None) -> None:
        super().__init__(f"User {user_id!r} is inactive.")
        self.user_id = user_id


class ProviderNotActiveError(ValueError):
    """Raised when the OAuthProviderConfig has ``is_active=False``.

    This indicates the provider was deactivated after a callback URL
    was already issued. The login MUST stop; the user-facing message
    is the standard "credentials invalid" exit.
    """

    def __init__(self, provider_code: str) -> None:
        super().__init__(f"OAuth provider {provider_code!r} is not active.")
        self.provider_code = provider_code


class EmailNotVerifiedError(ValueError):
    """Raised when the provider didn't assert email_verified=true and the
    provider config requires it (B.5.6 #1).

    The login MUST stop. The user-facing message is "please verify your
    email at the provider, then try again."
    """

    def __init__(self, *, email: str, provider_code: str) -> None:
        super().__init__(
            f"Provider {provider_code!r} did not assert verified email "
            "(or didn't supply an email)."
        )
        self.email = email
        self.provider_code = provider_code


class EmailDomainNotAllowedError(ValueError):
    """Raised when the user's email domain isn't in the provider's
    allowed_email_domains list (B.4.5).

    The login MUST stop. The user-facing message is generic
    ("this account isn't permitted via that provider") to avoid
    leaking the allowlist.
    """

    def __init__(self, *, email: str, allowed_domains: list[str]) -> None:
        super().__init__(
            f"Email {email!r} is not in the allowed domains for this provider."
        )
        self.email = email
        self.allowed_domains = allowed_domains


class ConflictingExternalIdentityError(ValueError):
    """Raised when an existing User has a different external identity
    for the same provider (B.4.7 #4).

    Example: the user has a SocialAccount linking
    ``(google-workspace, old-subject-id)`` to their account, but the
    callback now arrives with ``(google-workspace, new-subject-id)``
    for an email that matches the same user. This could be a legitimate
    provider-side migration OR an account-takeover attempt. Resolution
    requires manual support intervention (per B.4.7).

    The adapter (Phase 3) maps this to the account-linking help flow.
    """

    def __init__(
        self,
        *,
        user_id: UUID | str | None,
        provider_code: str,
        provider_uid: str,
    ) -> None:
        super().__init__(
            f"User {user_id!r} already has a different external identity "
            f"for provider {provider_code!r}."
        )
        self.user_id = user_id
        self.provider_code = provider_code
        # provider_uid is stored for support investigation but MUST NOT
        # be rendered to end users — it's a stable provider-side
        # identifier and could leak provider account information.
        self.provider_uid = provider_uid


class NoExistingUserAndSelfRegistrationDisabledError(ValueError):
    """Raised when there's no matching User by subject ID OR email, and
    the provider config has ``allow_self_registration=False``.

    The adapter (Phase 3) maps this to the "no active access /
    invitation required" exit page — the same page rendered when a
    user has zero memberships (B.4.4 branch 12a).
    """

    def __init__(self, *, email: str, provider_code: str) -> None:
        super().__init__(
            f"No existing user for email {email!r} via provider "
            f"{provider_code!r}, and self-registration is disabled."
        )
        self.email = email
        self.provider_code = provider_code


class LinkingNotAllowedError(ValueError):
    """Reserved for B.4.7 #5 — "user is completing an invite flow or
    passes a local confirmation challenge."

    Not raised in M1 D5 because B.4.7 #5 is enforced one level up
    (in the adapter / invite-flow). Defined here so the typed-exception
    surface is stable when M2 wires the invite flow.
    """

    def __init__(self, *, email: str, provider_code: str, reason: str) -> None:
        super().__init__(
            f"Account linking not allowed for {email!r} via {provider_code!r}: "
            f"{reason}"
        )
        self.email = email
        self.provider_code = provider_code
        self.reason = reason
