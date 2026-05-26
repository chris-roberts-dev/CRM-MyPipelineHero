"""revoke_all_handoff_tokens_for_user service (M1 D6 Phase 5, B.4.17).

Reads the ``user_handoffs:{user_id}`` Redis set, deletes each
``handoff:{tid}`` key, deletes the index set, and emits
``HANDOFF_TOKENS_REVOKED_BY_LOGOUT`` if any tokens were actually
revoked.

Called from the ``user_logged_out`` signal handler on root-domain
logout. Tenant-portal logout does NOT call this — tenant logout
destroys only that tenant's session, not the cross-tenant access
the root session provides.

**Failure mode.** Redis is operationally critical for the handoff
flow. If Redis is unreachable during logout, this function logs at
ERROR and returns 0 (no tokens revoked). The logout itself still
proceeds (the user's session is gone). Outstanding tokens then live
out their 60-second TTL. Net effect: a small window of "user
logged out but old handoff tokens still consumable" — bounded by
the TTL, never worse than the natural expiry.

**Known race window.** A token issued concurrently with revocation
may not appear in SMEMBERS (the SADD landed after the read). That
token survives logout until its own TTL expires. Tracked as a
known limitation for v1; Lua-script atomicity would close it but
adds operational complexity disproportionate to the risk.
"""

from __future__ import annotations

import logging
from uuid import UUID

from django.db import transaction

from apps.platform.accounts.handoff.services._redis_client import (
    get_handoff_redis_client,
)
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


def revoke_all_handoff_tokens_for_user(*, user_id: UUID) -> int:
    """Revoke all outstanding handoff tokens for a user.

    Args:
        user_id: The user whose outstanding tokens should be invalidated.

    Returns:
        Number of tokens revoked (0 if none outstanding or Redis is
        unreachable). The return value is informational; the
        ``HANDOFF_TOKENS_REVOKED_BY_LOGOUT`` audit event records the
        same count.
    """
    try:
        client = get_handoff_redis_client()
        index_key = f"user_handoffs:{user_id}"
        # Read first, then delete. Two round trips. A pipeline could
        # group these but the cost is negligible and the readability
        # is better as-is.
        token_ids_bytes = client.smembers(index_key)
        if not token_ids_bytes:
            # No outstanding tokens. Don't emit an audit event —
            # we'd flood the audit log with empty revocations on
            # every logout.
            return 0

        # SMEMBERS returns bytes; decode for use as key suffixes.
        token_ids = [
            tid.decode("ascii") if isinstance(tid, bytes) else tid
            for tid in token_ids_bytes
        ]

        # Bulk-delete primary nonces. DEL on a missing key is
        # tolerated (returns 0); concurrent consume of a token
        # between SMEMBERS and DEL means we DEL a missing key —
        # safe.
        keys_to_delete = [f"handoff:{tid}" for tid in token_ids]
        deleted_count = client.delete(*keys_to_delete)

        # Drop the index set.
        client.delete(index_key)

        # Emit audit event with the number of tokens we actually
        # found in the index. Different from deleted_count (which
        # may be lower if some were already consumed) — both are
        # informational; revoked_count is the more useful "intent"
        # figure.
        with transaction.atomic():
            audit_emit(
                "HANDOFF_TOKENS_REVOKED_BY_LOGOUT",
                actor_id=user_id,
                organization_id=None,
                object_kind="platform_accounts.User",
                object_id=str(user_id),
                metadata={
                    "tokens_in_index": len(token_ids),
                    "tokens_deleted": deleted_count,
                },
            )

        logger.info(
            "Revoked %d handoff tokens (deleted %d primary nonces) "
            "for user %s on root logout.",
            len(token_ids),
            deleted_count,
            user_id,
        )
        return len(token_ids)

    except Exception as exc:
        # Redis unreachable, or some other infrastructure failure.
        # Log loudly but don't propagate — logout itself must complete
        # successfully even if revocation fails. Outstanding tokens
        # will expire via TTL.
        logger.error(
            "Failed to revoke handoff tokens for user %s on logout: "
            "%s. Outstanding tokens will expire via TTL within 60s.",
            user_id,
            exc,
            exc_info=True,
        )
        return 0
