"""consume_handoff_token service (B.4.12, M1 D6 Phase 2).

Verifies a JWT, atomically consumes the Redis nonce, checks host
binding and membership status, and returns a HandoffResult.

The consume function uses GETDEL (Redis 6.2+) for atomic single-use
enforcement. This deviates from the guide's pipeline pattern
(GET + DELETE inside a MULTI/EXEC pipeline) for a stronger reason:
the pipeline pattern doesn't actually prevent concurrent consumes
from both seeing the same GET result before either DELETE lands.
GETDEL is a single command that returns the value AND deletes
atomically; concurrent calls either get the value (one wins) or
None (everyone else). See M1 D6 retro for the full justification.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import jwt
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest

from apps.platform.accounts.handoff.encryption import decrypt_handoff_secret
from apps.platform.accounts.handoff.models import HandoffSigningKey
from apps.platform.accounts.handoff.results import HandoffResult
from apps.platform.accounts.handoff.services._keys import (
    active_handoff_signing_keys_ordered_by_created_desc,
)
from apps.platform.accounts.handoff.services._redis_client import (
    get_handoff_redis_client,
)
from apps.platform.accounts.handoff.services.exceptions import (
    HandoffInvalidError,
)
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


def consume_handoff_token(*, token: str, request: HttpRequest) -> HandoffResult:
    """Verify, consume, and return a handoff result (B.4.12).

    The verification sequence:

    1. JWT signature verification, with kid-first lookup falling back
       to a trial loop over active signing keys.
    2. Atomic single-use enforcement via Redis GETDEL.
    3. Host check: request.get_host() matches the organization's
       tenant subdomain per MPH_TENANT_DOMAIN_TEMPLATE.
    4. Membership check: an ACTIVE Membership row matches the
       (user, organization) pair from the JWT.

    Any failure emits a structured audit event with a reason code and
    raises HandoffInvalidError. The caller MUST treat HandoffInvalidError
    as "do not establish a tenant session; render a generic error."

    Args:
        token: The JWT received from the issuing side.
        request: The HTTP request landing on the tenant subdomain.
            Used for ``request.get_host()`` for the host check.

    Returns:
        HandoffResult containing the verified user, org, membership,
        auth method/provider, and MFA satisfaction timestamp.

    Raises:
        HandoffInvalidError: verification failed. ``exc.reason`` is one
            of "expired", "invalid", "invalid_signature",
            "not_found_or_replayed", "host_mismatch",
            "membership_inactive", "organization_missing".
    """
    # ---- Step 1: JWT verification with kid-first / trial fallback. --------
    payload, used_key_id = _verify_jwt(token)
    token_id = payload["tid"]
    user_id = UUID(payload["uid"])
    organization_id = UUID(payload["oid"])
    membership_id = UUID(payload["mid"])

    # ---- Step 2: Atomic single-use enforcement. ---------------------------
    client = get_handoff_redis_client()
    redis_key = f"handoff:{token_id}"
    raw = client.getdel(redis_key)
    if raw is None:
        with transaction.atomic():
            audit_emit(
                "HANDOFF_REPLAY_DETECTED",
                actor_id=user_id,
                organization_id=organization_id,
                object_kind="platform_accounts.HandoffToken",
                object_id=token_id,
                metadata={
                    "reason": "not_found_or_replayed",
                    "key_id_used": used_key_id,
                    # Token itself is never logged.
                },
            )
        raise HandoffInvalidError("not_found_or_replayed")

    # ---- Step 3: Host check. ----------------------------------------------
    from apps.platform.organizations.models import (
        Membership,
        MembershipStatus,
        Organization,
    )

    try:
        org = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        # Token references an org that doesn't exist (deleted between
        # issue and consume, or token was forged with a bad oid claim).
        # We've already consumed the Redis nonce above, so the audit
        # event is the only side effect.
        with transaction.atomic():
            audit_emit(
                "HANDOFF_HOST_MISMATCH",
                actor_id=user_id,
                organization_id=None,
                object_kind="platform_accounts.HandoffToken",
                object_id=token_id,
                metadata={
                    "reason": "organization_missing",
                    "claimed_organization_id": str(organization_id),
                },
            )
        raise HandoffInvalidError("organization_missing")

    expected_host = settings.MPH_TENANT_DOMAIN_TEMPLATE.format(slug=org.slug)
    actual_host = request.get_host().split(":")[0]  # strip port if present
    expected_host_no_port = expected_host.split(":")[0]
    if actual_host != expected_host_no_port:
        with transaction.atomic():
            audit_emit(
                "HANDOFF_HOST_MISMATCH",
                actor_id=user_id,
                organization_id=organization_id,
                object_kind="platform_accounts.HandoffToken",
                object_id=token_id,
                metadata={
                    "reason": "host_mismatch",
                    "expected_host": expected_host_no_port,
                    "actual_host": actual_host,
                },
            )
        raise HandoffInvalidError("host_mismatch")

    # ---- Step 4: Membership check. ----------------------------------------
    try:
        membership = Membership.objects.get(
            id=membership_id,
            user_id=user_id,
            organization_id=organization_id,
            status=MembershipStatus.ACTIVE,
        )
    except Membership.DoesNotExist:
        with transaction.atomic():
            audit_emit(
                "HANDOFF_TOKEN_CONSUMED",
                actor_id=user_id,
                organization_id=organization_id,
                object_kind="platform_accounts.HandoffToken",
                object_id=token_id,
                metadata={
                    "outcome": "membership_inactive",
                    "membership_id": str(membership_id),
                },
            )
        raise HandoffInvalidError("membership_inactive")

    # ---- Step 5: Success — emit audit events, return result. --------------
    with transaction.atomic():
        # If we verified with a non-primary key, the operator is mid-
        # rotation. Surface this so they can confirm the overlap window
        # is working and old tokens are clearing.
        active = active_handoff_signing_keys_ordered_by_created_desc()
        if active and used_key_id != active[0].key_id:
            audit_emit(
                "HANDOFF_VERIFIED_WITH_RETIRED_KEY",
                actor_id=user_id,
                organization_id=organization_id,
                object_kind="platform_accounts.HandoffSigningKey",
                object_id=used_key_id,
                metadata={
                    "used_key_id": used_key_id,
                    "current_primary_key_id": active[0].key_id,
                    "token_id": token_id,
                },
            )

        audit_emit(
            "HANDOFF_TOKEN_CONSUMED",
            actor_id=user_id,
            organization_id=organization_id,
            object_kind="platform_accounts.HandoffToken",
            object_id=token_id,
            metadata={
                "outcome": "success",
                "key_id_used": used_key_id,
                "auth_method": payload["amr"],
                "auth_provider": payload.get("apr"),
            },
        )

    return HandoffResult(
        user_id=user_id,
        organization_id=organization_id,
        membership_id=membership.id,
        auth_method=payload["amr"],
        auth_provider=payload.get("apr"),
        mfa_satisfied_at=_parse_iso_datetime(payload["mfa"]),
    )


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _verify_jwt(token: str) -> tuple[dict[str, Any], str]:
    """Verify the JWT signature against active signing keys.

    Strategy:
    1. Read unverified ``kid`` header.
    2. If kid present and matches an active key, try that key first.
    3. Otherwise, trial-loop over active keys (newest first).
    4. Catch expired-token before invalid-signature so the audit
       reason is correct (expired → "expired", bad sig → "invalid_signature").

    Returns:
        (payload, used_key_id) tuple on success.

    Raises:
        HandoffInvalidError: with reason "expired", "invalid", or
        "invalid_signature".
    """
    active_keys = active_handoff_signing_keys_ordered_by_created_desc()
    if not active_keys:
        # No active keys means no verification can succeed. Treat as
        # invalid_signature for audit-categorization consistency.
        raise HandoffInvalidError("invalid_signature")

    # Try to read the kid header without verifying — failure here is
    # a malformed JWT.
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise HandoffInvalidError("invalid") from exc

    kid_hint = header.get("kid")

    # Build the verification key order: kid match first (if any),
    # then everyone else.
    keys_to_try: list[HandoffSigningKey] = []
    if kid_hint:
        hinted = [k for k in active_keys if k.key_id == kid_hint]
        keys_to_try.extend(hinted)
        keys_to_try.extend(k for k in active_keys if k.key_id != kid_hint)
    else:
        keys_to_try.extend(active_keys)

    last_error: Exception | None = None
    for signing_key in keys_to_try:
        secret_bytes = decrypt_handoff_secret(signing_key.secret)
        try:
            payload = jwt.decode(
                token,
                secret_bytes,
                algorithms=[signing_key.algorithm],
                options={"require": ["exp", "iat", "tid", "uid", "oid", "mid"]},
            )
            return payload, signing_key.key_id
        except jwt.ExpiredSignatureError as exc:
            # Expired is terminal — no other key would help.
            raise HandoffInvalidError("expired") from exc
        except jwt.InvalidSignatureError as exc:
            # Signature mismatch for this key; try next.
            last_error = exc
            continue
        except jwt.MissingRequiredClaimError as exc:
            # Payload structurally invalid.
            raise HandoffInvalidError("invalid") from exc
        except jwt.InvalidTokenError as exc:
            # Any other JWT-level failure.
            raise HandoffInvalidError("invalid") from exc

    # No active key verified the token.
    raise HandoffInvalidError("invalid_signature") from last_error


def _parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime string.

    Python 3.14 datetime.fromisoformat handles full ISO 8601 including
    timezone info — no need for python-dateutil here.
    """
    return datetime.fromisoformat(value)
