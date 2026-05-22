"""issue_handoff_token service (B.4.12, M1 D6 Phase 2).

Mints a JWT signed with the current primary HandoffSigningKey,
writes a Redis nonce keyed by the token id, and emits
``HANDOFF_TOKEN_ISSUED``.

Per project posture:
* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` for audit emission. Redis writes
  happen INSIDE the atomic block but are not themselves transactional
  (Redis nonce isn't undone if the audit emit fails). This is a
  deliberate consistency tradeoff: if audit fails, the Redis nonce
  expires naturally in 60s, and the token is never returned to the
  caller because the function re-raises. Net effect: token is unusable
  even though the nonce briefly exists.
* Audit emitted inside the atomic boundary.
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID

import jwt
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.platform.accounts.handoff.encryption import decrypt_handoff_secret
from apps.platform.accounts.handoff.services._keys import (
    active_handoff_signing_keys_ordered_by_created_desc,
)
from apps.platform.accounts.handoff.services._redis_client import (
    get_handoff_redis_client,
)
from apps.platform.accounts.handoff.services.exceptions import (
    HandoffInvalidIssueParamError,
    NoActiveHandoffSigningKeyError,
)
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


# B.4.14: allowed values for auth_method on the tenant-local session.
# Issuance validates against this set so bad values can't end up in
# JWTs (which then propagate to the session and audit log).
_ALLOWED_AUTH_METHODS: frozenset[str] = frozenset(
    {"password", "oidc", "oauth2", "impersonation"}
)

# How stale can mfa_satisfied_at be when we mint the token?
# The caller (org-picker view in Phase 4) is supposed to enforce
# B.4.10's 5-minute window, but we add a defensive upper bound here
# so a misconfigured caller can't issue tokens claiming MFA from days
# ago. 1 hour is generous and catches obvious bugs without conflict-
# ing with the 5-minute B.4.10 window the caller enforces.
_MAX_MFA_SATISFIED_STALENESS = timedelta(hours=1)


def issue_handoff_token(
    *,
    user_id: UUID,
    organization_id: UUID,
    membership_id: UUID,
    auth_method: str,
    auth_provider: str | None,
    mfa_satisfied_at: datetime,
) -> str:
    """Mint a cross-subdomain handoff token (B.4.12).

    The returned string is a signed JWT (HS256). The caller embeds
    it in a POST form action targeting the tenant subdomain's
    handoff-consume endpoint.

    Args:
        user_id: The User the handoff is for.
        organization_id: The target tenant.
        membership_id: The Membership authorizing the handoff. Must
            reference an ACTIVE membership for this user+org.
        auth_method: How the user authenticated on root domain. Must
            be one of "password", "oidc", "oauth2", "impersonation".
        auth_provider: provider_code if OAuth/OIDC, else None.
        mfa_satisfied_at: Wall-clock timestamp of MFA satisfaction.

    Returns:
        The signed JWT as an ASCII string.

    Raises:
        HandoffInvalidIssueParamError: any parameter failed validation.
        NoActiveHandoffSigningKeyError: no non-retired signing key
            available; operator must rotate a key in.
    """
    _validate_issue_params(
        user_id=user_id,
        organization_id=organization_id,
        membership_id=membership_id,
        auth_method=auth_method,
        mfa_satisfied_at=mfa_satisfied_at,
    )

    active_keys = active_handoff_signing_keys_ordered_by_created_desc()
    if not active_keys:
        raise NoActiveHandoffSigningKeyError(
            "No non-retired HandoffSigningKey exists. Platform admin "
            "must create + promote a key before handoff tokens can "
            "be issued."
        )
    primary_key = active_keys[0]
    secret_bytes = decrypt_handoff_secret(primary_key.secret)

    # 256 bits of randomness per B.4.13.
    token_id = secrets.token_urlsafe(32)
    issued_at = timezone.now()
    ttl = settings.MPH_HANDOFF_TOKEN_TTL_SECONDS
    expires_at = issued_at + timedelta(seconds=ttl)

    payload = {
        "tid": token_id,
        "uid": str(user_id),
        "oid": str(organization_id),
        "mid": str(membership_id),
        "amr": auth_method,
        "apr": auth_provider,
        "mfa": mfa_satisfied_at.isoformat(),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    headers = {"kid": primary_key.key_id}

    signed = jwt.encode(
        payload,
        secret_bytes,
        algorithm=primary_key.algorithm,
        headers=headers,
    )
    # PyJWT >= 2 returns str by default; older versions returned bytes.
    if isinstance(signed, bytes):
        signed = signed.decode("ascii")

    with transaction.atomic():
        # Redis nonce — atomic single-use enforcement counterpart.
        # Value is just the timestamp; the GETDEL at consume time
        # returns this value, proving the nonce existed.
        client = get_handoff_redis_client()
        redis_key = f"handoff:{token_id}"
        client.setex(
            redis_key,
            ttl,
            json.dumps(
                {
                    "issued_at": issued_at.isoformat(),
                    "uid": str(user_id),
                    "oid": str(organization_id),
                    "mid": str(membership_id),
                }
            ),
        )

        audit_emit(
            "HANDOFF_TOKEN_ISSUED",
            actor_id=user_id,
            organization_id=organization_id,
            object_kind="platform_accounts.HandoffSigningKey",
            object_id=str(primary_key.id),
            metadata={
                "token_id": token_id,
                "key_id": primary_key.key_id,
                "auth_method": auth_method,
                "auth_provider": auth_provider,
                "ttl_seconds": ttl,
                # NOTE: the token itself is never logged. Only token_id
                # (a non-secret identifier) appears in audit metadata.
            },
        )

    return signed


def _validate_issue_params(
    *,
    user_id: UUID,
    organization_id: UUID,
    membership_id: UUID,
    auth_method: str,
    mfa_satisfied_at: datetime,
) -> None:
    """Validate issue parameters; raise HandoffInvalidIssueParamError on failure."""
    from apps.platform.organizations.models import Membership, MembershipStatus

    if auth_method not in _ALLOWED_AUTH_METHODS:
        raise HandoffInvalidIssueParamError(
            f"auth_method={auth_method!r} is not in the allowed set "
            f"{sorted(_ALLOWED_AUTH_METHODS)!r}"
        )

    if mfa_satisfied_at.tzinfo is None:
        raise HandoffInvalidIssueParamError(
            "mfa_satisfied_at must be a timezone-aware datetime"
        )

    now = timezone.now()
    if mfa_satisfied_at > now + timedelta(seconds=5):
        # 5-second skew tolerance for clock drift across processes.
        raise HandoffInvalidIssueParamError("mfa_satisfied_at is in the future")
    if now - mfa_satisfied_at > _MAX_MFA_SATISFIED_STALENESS:
        raise HandoffInvalidIssueParamError(
            f"mfa_satisfied_at is more than {_MAX_MFA_SATISFIED_STALENESS} "
            f"old; refusing to issue token"
        )

    # Verify the membership exists, is active, and references this user+org.
    try:
        membership = Membership.objects.get(id=membership_id)
    except Membership.DoesNotExist as exc:
        raise HandoffInvalidIssueParamError(
            f"membership_id={membership_id!r} does not exist"
        ) from exc

    if membership.user_id != user_id:
        raise HandoffInvalidIssueParamError(
            f"membership_id={membership_id!r} belongs to a different user"
        )
    if membership.organization_id != organization_id:
        raise HandoffInvalidIssueParamError(
            f"membership_id={membership_id!r} belongs to a different " f"organization"
        )
    if membership.status != MembershipStatus.ACTIVE:
        raise HandoffInvalidIssueParamError(
            f"membership_id={membership_id!r} is not ACTIVE "
            f"(status={membership.status!r})"
        )
