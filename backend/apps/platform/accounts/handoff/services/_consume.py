"""consume_handoff_token service (B.4.12, M1 D6 Phase 2 + Phase 5, M1 D7 Phase 5).

Verifies a JWT, atomically consumes the Redis nonce, removes the
token id from the per-user secondary index, checks host binding and
membership status, and returns a HandoffResult.

**M1 D7 Phase 5 — Impersonation claim.**

If the JWT carries an ``iai`` claim, the consume service parses it
into a UUID and populates ``HandoffResult.impersonator_admin_id``.
Absent ``iai`` means a regular (non-impersonation) handoff.

The ``iai`` claim is NOT in the required-claims list — its presence
is optional. Existing non-impersonation tokens (issued without it)
continue to verify cleanly.
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
    """Verify, consume, and return a handoff result (B.4.12)."""
    # ---- Step 1: JWT verification with kid-first / trial fallback. --------
    payload, used_key_id = _verify_jwt(token)
    token_id = payload["tid"]
    user_id = UUID(payload["uid"])
    organization_id = UUID(payload["oid"])
    membership_id = UUID(payload["mid"])

    # Phase 5: parse optional iai claim. Absent → non-impersonation.
    iai_raw = payload.get("iai")
    impersonator_admin_id: UUID | None = UUID(iai_raw) if iai_raw is not None else None

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
                },
            )
        raise HandoffInvalidError("not_found_or_replayed")

    # ---- Step 3: Best-effort secondary-index cleanup. ---------------------
    try:
        client.srem(f"user_handoffs:{user_id}", token_id)
    except Exception as exc:
        logger.warning(
            "Failed to remove consumed token from user_handoffs index "
            "(user=%s, token_id=%s): %s. Set TTL will clean up.",
            user_id,
            token_id,
            exc,
        )

    # ---- Step 4: Host check. ----------------------------------------------
    from apps.platform.organizations.models import (
        Membership,
        MembershipStatus,
        Organization,
    )

    try:
        org = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
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
    actual_host = request.get_host().split(":")[0]
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

    # ---- Step 5: Membership check. ----------------------------------------
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

    # ---- Step 6: Success — emit audit events, return result. --------------
    with transaction.atomic():
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

        consume_metadata: dict[str, Any] = {
            "outcome": "success",
            "key_id_used": used_key_id,
            "auth_method": payload["amr"],
            "auth_provider": payload.get("apr"),
        }
        if impersonator_admin_id is not None:
            consume_metadata["impersonator_admin_id"] = str(impersonator_admin_id)

        audit_emit(
            "HANDOFF_TOKEN_CONSUMED",
            actor_id=user_id,
            organization_id=organization_id,
            object_kind="platform_accounts.HandoffToken",
            object_id=token_id,
            metadata=consume_metadata,
        )

    return HandoffResult(
        user_id=user_id,
        organization_id=organization_id,
        membership_id=membership.id,
        auth_method=payload["amr"],
        auth_provider=payload.get("apr"),
        mfa_satisfied_at=_parse_iso_datetime(payload["mfa"]),
        impersonator_admin_id=impersonator_admin_id,
    )


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _verify_jwt(token: str) -> tuple[dict[str, Any], str]:
    """Verify the JWT signature against active signing keys."""
    active_keys = active_handoff_signing_keys_ordered_by_created_desc()
    if not active_keys:
        raise HandoffInvalidError("invalid_signature")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise HandoffInvalidError("invalid") from exc

    kid_hint = header.get("kid")

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
            raise HandoffInvalidError("expired") from exc
        except jwt.InvalidSignatureError as exc:
            last_error = exc
            continue
        except jwt.MissingRequiredClaimError as exc:
            raise HandoffInvalidError("invalid") from exc
        except jwt.InvalidTokenError as exc:
            raise HandoffInvalidError("invalid") from exc

    raise HandoffInvalidError("invalid_signature") from last_error


def _parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO 8601 datetime string."""
    return datetime.fromisoformat(value)
