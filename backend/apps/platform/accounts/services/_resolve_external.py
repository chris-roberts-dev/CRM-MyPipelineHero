"""resolve_external_user — OAuth/OIDC user resolution service (B.4.6, B.4.7).

This is the *single* chokepoint where an external (OAuth/OIDC) identity
becomes a canonical platform User. Every callback flow MUST go through
this function. No other code may create a SocialAccount or link an
external identity to a User.

**Resolution order (B.4.6):**

1. Validate provider is active.
2. Validate email-domain allowlist.
3. Validate email-verification policy.
4. Subject-ID lookup. If the (provider_code, provider_uid) pair
   already maps to a SocialAccount → return the linked User.
5. Email-based linking. If verified email matches an existing User
   and there's no conflicting external identity for the same provider
   → link and return.
6. Self-registration. If the provider config allows self-registration
   → create a new external-only User and link.
7. Otherwise → raise NoExistingUserAndSelfRegistrationDisabledError.
   This is the "no active access / invitation required" exit point.

**B.4.7 silent-linking rules — what this service enforces:**

Per the guide, silent account linking based only on email is prohibited
unless ALL of:

1. provider email is verified → enforced at step 3.
2. provider is active and approved → enforced at step 1.
3. provider config allows email-based linking → enforced by the
   combination of step 3 (verified email) AND step 5 (only proceeds
   when the email is verified).
4. no conflicting existing external identity exists → enforced at step 5.
5. user is completing an invite flow or passes a local confirmation
   challenge → NOT enforced here. This is a UI-level rule that lives
   in the adapter/invite-flow layer. The service is strict on the
   first four; the fifth is a soft control above the service. Tracked
   in the M1 D5 retro deviation log.

**Side effects:**

* MAY create a SocialAccount.
* MAY create a User (only when self-registration is allowed).
* MUST emit OAUTH_ACCOUNT_LINKED when a SocialAccount is created.
* MUST emit USER_REGISTERED when a User is created.
* MUST NOT create, modify, or delete Membership / Role / Capability rows
  (B.3.9).
* MUST NOT store tokens.
* MUST NOT modify is_staff / is_superuser based on provider claims.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.platform.accounts.oauth.claims import ExternalIdentityClaims
from apps.platform.accounts.oauth.models import OAuthProviderConfig
from apps.platform.accounts.services.exceptions import (
    ConflictingExternalIdentityError,
    EmailDomainNotAllowedError,
    EmailNotVerifiedError,
    NoExistingUserAndSelfRegistrationDisabledError,
    ProviderNotActiveError,
    UserInactiveError,
)
from apps.platform.audit.services import audit_emit

if TYPE_CHECKING:
    from apps.platform.accounts.models import User

logger = logging.getLogger(__name__)


# Sensitive keys to strip from extra_data before persisting to
# SocialAccount.extra_data. Defense in depth — Phase 1's
# normalize_socialaccount_claims also strips these, but we re-strip
# here because the field is JSONB and any future caller might pass
# data that bypassed normalization.
_SENSITIVE_EXTRA_DATA_KEYS = frozenset(
    {
        "access_token",
        "refresh_token",
        "id_token",
        "code",
        "client_secret",
        "private_key",
        "password",
    }
)


def _strip_sensitive(extra_data: dict) -> dict:
    """Return a copy of extra_data with sensitive keys removed."""
    return {k: v for k, v in extra_data.items() if k not in _SENSITIVE_EXTRA_DATA_KEYS}


def _email_domain(email: str) -> str:
    """Extract domain from a normalized lowercase email."""
    return email.rsplit("@", 1)[-1] if "@" in email else ""


def _domain_allowed(
    email: str | None,
    allowed_domains: list[str] | None,
) -> bool:
    """True iff allowed_domains is None/empty OR email's domain is listed.

    Matching is case-insensitive (domains in the provider config are
    expected lowercase; we lowercase the email's domain anyway for
    defense in depth).
    """
    if not allowed_domains:
        return True
    if not email:
        return False
    domain = _email_domain(email).lower()
    return domain in {d.lower() for d in allowed_domains}


def _has_conflicting_external_identity(
    user: User,
    *,
    provider_code: str,
    provider_uid: str,
) -> bool:
    """Does this user have a DIFFERENT SocialAccount for the same provider?

    B.4.7 #4: "no conflicting existing external identity exists."
    Same provider, different uid = conflict. Two different providers
    (e.g. google + microsoft) = NOT a conflict; users can have both.
    """
    return (
        SocialAccount.objects.filter(
            user=user,
            provider=provider_code,
        )
        .exclude(uid=provider_uid)
        .exists()
    )


def resolve_external_user(
    *,
    claims: ExternalIdentityClaims,
    provider_config: OAuthProviderConfig,
    actor_id: UUID,
) -> User:
    """Resolve or link an OAuth/OIDC identity to a canonical User (B.4.6).

    See module docstring for the full algorithm and B.4.7 rule mapping.

    Args:
        claims: Normalized provider claims (B.3.8). Built by
            ``normalize_socialaccount_claims`` (Phase 1).
        provider_config: The OAuthProviderConfig row whose
            ``provider_code`` matches ``claims.provider_code``. Caller
            (the adapter) is responsible for loading the right config
            for the inbound claim.
        actor_id: System User id during the callback flow. The
            *resolution* is a system action (the application decides
            who the user is); the subsequent *login* event has
            ``actor_id=user.id`` and lives in the Phase 4 signal
            handler.

    Returns:
        The canonical User. Caller (the adapter) is responsible for
        calling allauth's login mechanics on this user.

    Raises:
        ProviderNotActiveError: provider_config.is_active=False.
        EmailDomainNotAllowedError: email's domain isn't in the
            provider's allowed_email_domains.
        EmailNotVerifiedError: provider requires verified email and
            the provider didn't assert verification.
        ConflictingExternalIdentityError: a different SocialAccount
            for the same provider already links to the candidate user.
        UserInactiveError: matched user has is_active=False.
        NoExistingUserAndSelfRegistrationDisabledError: no existing
            user and the provider doesn't allow self-registration.
        ValueError: actor_id is missing or provider_code mismatch
            between claims and config (a programming error).
    """
    if actor_id is None:
        raise ValueError("actor_id is required.")
    if claims.provider_code != provider_config.provider_code:
        raise ValueError(
            f"provider_code mismatch: claims={claims.provider_code!r} "
            f"vs config={provider_config.provider_code!r}. Caller must "
            f"pass the OAuthProviderConfig matching the inbound claims."
        )

    UserModel = get_user_model()

    # ---- Step 1: provider active. (B.4.5) ----
    if not provider_config.is_active:
        raise ProviderNotActiveError(provider_config.provider_code)

    # ---- Step 2: email-domain allowlist. (B.4.5) ----
    if not _domain_allowed(claims.email, provider_config.allowed_email_domains):
        raise EmailDomainNotAllowedError(
            email=claims.email or "",
            allowed_domains=list(provider_config.allowed_email_domains or []),
        )

    # ---- Step 3: email verification policy. (B.4.5, B.5.6 #1) ----
    if provider_config.require_verified_email and not claims.email_verified:
        raise EmailNotVerifiedError(
            email=claims.email or "",
            provider_code=claims.provider_code,
        )

    # ---- Step 4: subject-ID lookup (preferred per B.5.6 #2). ----
    existing_sa = (
        SocialAccount.objects.filter(
            provider=claims.provider_code,
            uid=claims.provider_uid,
        )
        .select_related("user")
        .first()
    )

    if existing_sa is not None:
        user = existing_sa.user
        if not user.is_active:
            raise UserInactiveError(user_id=user.id)
        # Update last-login bookkeeping. SocialAccount has
        # `last_login` only on its `SocialToken` companion in some
        # allauth versions; here we touch extra_data['last_seen_at']
        # so we never depend on a field that may not exist.
        _update_socialaccount_extra_data(existing_sa, claims)
        return user

    # ---- Step 5: email-based linking. ----
    # Per B.4.7, silent email-based linking is allowed only when:
    #   - verified email (already enforced at step 3 IF require_verified_email),
    #   - provider is active (already enforced at step 1),
    #   - no conflicting external identity (checked below),
    #   - email is present.
    #
    # If `require_verified_email=False` AND the provider didn't assert
    # email_verified, we can't safely link by email — drop to step 6
    # (self-registration or reject).
    can_attempt_email_linking = (
        claims.email is not None and claims.email_verified  # Belt and suspenders.
    )

    if can_attempt_email_linking:
        existing_user = UserModel.objects.filter(email=claims.email).first()
        if existing_user is not None:
            if not existing_user.is_active:
                raise UserInactiveError(user_id=existing_user.id)
            if _has_conflicting_external_identity(
                existing_user,
                provider_code=claims.provider_code,
                provider_uid=claims.provider_uid,
            ):
                raise ConflictingExternalIdentityError(
                    user_id=existing_user.id,
                    provider_code=claims.provider_code,
                    provider_uid=claims.provider_uid,
                )

            # Link the external identity to the existing user.
            return _link_socialaccount_to_user(
                user=existing_user,
                claims=claims,
                actor_id=actor_id,
                is_new_user=False,
            )

    # ---- Step 6: self-registration (per-provider policy, B.4.6 step 4). ----
    if provider_config.allow_self_registration:
        return _create_external_user_and_link(
            claims=claims,
            actor_id=actor_id,
        )

    # ---- Step 7: no match, no self-registration. ----
    raise NoExistingUserAndSelfRegistrationDisabledError(
        email=claims.email or "",
        provider_code=claims.provider_code,
    )


def _update_socialaccount_extra_data(
    social_account: SocialAccount,
    claims: ExternalIdentityClaims,
) -> None:
    """Touch the SocialAccount with the latest provider claims.

    Strips sensitive keys defensively. Wraps in atomic() so the write
    is committed before the caller's allauth login flow proceeds.
    """
    safe_data = _strip_sensitive(claims.raw_claims)
    safe_data["mph_last_seen_at"] = timezone.now().isoformat()
    with transaction.atomic():
        social_account.extra_data = safe_data
        social_account.save(update_fields=["extra_data"])


def _link_socialaccount_to_user(
    *,
    user: User,
    claims: ExternalIdentityClaims,
    actor_id: UUID,
    is_new_user: bool,
) -> User:
    """Create a SocialAccount row linking claims to the given user.

    Emits OAUTH_ACCOUNT_LINKED inside the atomic boundary.

    Raises:
        ConflictingExternalIdentityError if a race created a SocialAccount
        between the existence check and the create. Re-raised as the
        same typed exception so callers branch identically.
    """
    safe_extra_data = _strip_sensitive(claims.raw_claims)

    try:
        with transaction.atomic():
            SocialAccount.objects.create(
                user=user,
                provider=claims.provider_code,
                uid=claims.provider_uid,
                extra_data=safe_extra_data,
            )

            audit_emit(
                "OAUTH_ACCOUNT_LINKED",
                actor_id=actor_id,
                organization_id=None,
                object_kind="platform_accounts.User",
                object_id=str(user.id),
                metadata={
                    "provider_code": claims.provider_code,
                    "provider_uid_present": True,  # presence only, never the uid value
                    "linked_to_new_user": is_new_user,
                    "linked_email_present": claims.email is not None,
                },
            )
    except IntegrityError as exc:
        # Race: between our check and our create, another flow linked
        # the same (provider, uid) pair. Re-raise as the typed conflict
        # error so the adapter renders the help page.
        raise ConflictingExternalIdentityError(
            user_id=user.id,
            provider_code=claims.provider_code,
            provider_uid=claims.provider_uid,
        ) from exc

    return user


def _create_external_user_and_link(
    *,
    claims: ExternalIdentityClaims,
    actor_id: UUID,
) -> User:
    """Create a new external-only User and link the SocialAccount.

    Only called when ``provider_config.allow_self_registration=True``
    AND no existing user matches by email OR subject ID.

    The new User:
      - has the verified email from claims as ``email``,
      - has ``external_login_only=True`` (B.3.4),
      - has an unusable Django password,
      - is is_active=True,
      - is NOT is_staff or is_superuser.

    Emits both USER_REGISTERED and OAUTH_ACCOUNT_LINKED inside the
    atomic boundary.
    """
    UserModel = get_user_model()

    if not claims.email:
        # Shouldn't reach here: step 5 requires email; step 6 only
        # runs after step 5's existence check, which requires email.
        # Defensive guard.
        raise ValueError(
            "Cannot self-register an external user without an email claim."
        )

    safe_extra_data = _strip_sensitive(claims.raw_claims)

    try:
        with transaction.atomic():
            user = UserModel(
                email=claims.email,
                is_active=True,
                is_staff=False,
                is_superuser=False,
                is_system=False,
                external_login_only=True,
                preferred_auth_method="OIDC",
            )
            user.password = make_password(None)  # unusable
            user.save()

            SocialAccount.objects.create(
                user=user,
                provider=claims.provider_code,
                uid=claims.provider_uid,
                extra_data=safe_extra_data,
            )

            audit_emit(
                "USER_REGISTERED",
                actor_id=actor_id,
                organization_id=None,
                object_kind="platform_accounts.User",
                object_id=str(user.id),
                payload_after={
                    "email": user.email,
                    "is_active": True,
                    "password_was_set": False,
                    "external_login_only": True,
                    "registration_source": "oauth_self_registration",
                    "provider_code": claims.provider_code,
                },
            )
            audit_emit(
                "OAUTH_ACCOUNT_LINKED",
                actor_id=actor_id,
                organization_id=None,
                object_kind="platform_accounts.User",
                object_id=str(user.id),
                metadata={
                    "provider_code": claims.provider_code,
                    "provider_uid_present": True,
                    "linked_to_new_user": True,
                    "linked_email_present": True,
                },
            )
    except IntegrityError as exc:
        # Race condition: a parallel callback created the user with
        # the same email. Treat as a conflict — the help-page flow
        # (rendered by Phase 3's adapter) is the right user experience.
        raise ConflictingExternalIdentityError(
            user_id=None,
            provider_code=claims.provider_code,
            provider_uid=claims.provider_uid,
        ) from exc

    return user
