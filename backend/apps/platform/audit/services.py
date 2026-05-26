"""Audit emission interface (G.5.3) — M1 stub.

The full implementation, with partitioned ``platform_audit.AuditEvent``
rows + masking + retention, lands in M2 (J.4). M1's contract surface
matches the documented :func:`audit_emit` signature exactly so service
code written against it today won't need to change in M2.

**Behavior in M1:**

* Validates that a database transaction is open (per G.5.3 "raises if
  not within a transaction"). This enforces the discipline that audit
  events are emitted alongside the state change they describe, in the
  same atomic boundary, so the audit row commits if and only if the
  state change commits.
* If audit recording is enabled (``MPH_AUDIT_RECORDING=True`` in
  settings, default ``True`` in dev/test, default ``False`` in prod),
  appends an :class:`AuditEvent` named-tuple to a thread-local buffer.
  Tests use :func:`captured_audit_events` to assert emission.
* Otherwise, the event is dropped silently. The M2 implementation will
  replace this with a database insert.

**Event registry deviations from G.5.2:**

M1 D2 adds `ORG_CREATED` / `MEMBERSHIP_CREATED`. M1 D4 adds
`USER_REGISTERED` and MFA lifecycle codes. M1 D6 Phase 1 adds the
handoff-signing-key lifecycle codes. M1 D6 Phase 4B adds the
session-establishment codes (`TENANT_SESSION_ESTABLISHED`,
`MEMBERSHIP_SELECTED`). M1 D6 Phase 5 adds the logout-and-revocation
codes (`ROOT_SESSION_LOGOUT`, `TENANT_SESSION_LOGOUT`,
`HANDOFF_TOKENS_REVOKED_BY_LOGOUT`). All these additions will be
folded into G.5.2 during M2 audit work.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditEvent:
    """In-memory representation of an audit event."""

    event_type: str
    actor_id: UUID | None
    organization_id: UUID | None
    object_kind: str | None = None
    object_id: str | None = None
    payload_before: dict[str, Any] | None = None
    payload_after: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    on_behalf_of_id: UUID | None = None
    extras: dict[str, Any] = field(default_factory=dict)


_local = threading.local()


def is_audit_recording_enabled() -> bool:
    return bool(getattr(settings, "MPH_AUDIT_RECORDING", False))


def _buffer() -> list[AuditEvent]:
    if not hasattr(_local, "buffer"):
        _local.buffer = []
    return _local.buffer  # type: ignore[no-any-return]


def captured_audit_events(
    *,
    event_type: str | None = None,
    organization_id: UUID | None = None,
) -> list[AuditEvent]:
    out = list(_buffer())
    if event_type is not None:
        out = [e for e in out if e.event_type == event_type]
    if organization_id is not None:
        out = [e for e in out if e.organization_id == organization_id]
    return out


def reset_captured_audit_events() -> None:
    _local.buffer = []


_KNOWN_EVENT_TYPES: frozenset[str] = frozenset(
    {
        # M1 D2.
        "ORG_CREATED",
        "MEMBERSHIP_CREATED",
        # M1 D4.
        "USER_REGISTERED",
        "MFA_ENROLLED",
        "MFA_DISABLED",
        "MFA_RECOVERY_CODES_REGENERATED",
        "MFA_RECOVERY_CODE_CONSUMED",
        # M1 D6 Phase 1 — Handoff signing-key lifecycle (B.4.13.1).
        "HANDOFF_SIGNING_KEY_CREATED",
        "HANDOFF_SIGNING_KEY_PROMOTED",
        "HANDOFF_SIGNING_KEY_RETIRED",
        "HANDOFF_SIGNING_KEY_EMERGENCY_ROTATED",
        "HANDOFF_VERIFIED_WITH_RETIRED_KEY",
        # M1 D6 Phase 4B — Tenant-session establishment + picker.
        "TENANT_SESSION_ESTABLISHED",
        "MEMBERSHIP_SELECTED",
        # M1 D6 Phase 5 — Logout + token revocation (B.4.17).
        "ROOT_SESSION_LOGOUT",
        "TENANT_SESSION_LOGOUT",
        "HANDOFF_TOKENS_REVOKED_BY_LOGOUT",
        # G.5.2 Membership / RBAC.
        "ROLE_ASSIGNED",
        "MEMBER_INVITED",
        "MEMBER_ACCEPTED_INVITE",
        "MEMBERSHIP_DEACTIVATED",
        "MEMBERSHIP_SUSPENDED",
        "MEMBERSHIP_REINSTATED",
        "MEMBERSHIP_REACTIVATED",
        "ROLE_SAVED",
        "ROLE_UNASSIGNED",
        "CAPABILITY_GRANT_APPLIED",
        "ORG_SETTINGS_UPDATED",
        # G.5.2 Tenant lifecycle.
        "TENANT_EXPORT_REQUESTED",
        "TENANT_EXPORT_ASSEMBLED",
        "TENANT_EXPORT_DOWNLOADED",
        "TENANT_DELETION_REQUESTED",
        "TENANT_DELETION_GRACE_STARTED",
        "TENANT_DELETION_EXECUTED",
        "TENANT_DELETION_CANCELLED",
        # B.4.19 Authentication.
        "LOGIN_STARTED",
        "LOGIN_SUCCEEDED",
        "LOGIN_FAILED",
        "LOCAL_PASSWORD_LOGIN_SUCCEEDED",
        "LOCAL_PASSWORD_LOGIN_FAILED",
        "LOCAL_MFA_CHALLENGE_REQUIRED",
        "LOCAL_MFA_CHALLENGE_PASSED",
        "LOCAL_MFA_CHALLENGE_FAILED",
        "OAUTH_LOGIN_STARTED",
        "OAUTH_LOGIN_SUCCEEDED",
        "OAUTH_LOGIN_FAILED",
        "OAUTH_ACCOUNT_LINKED",
        "OAUTH_ACCOUNT_UNLINKED",
        "OAUTH_PROVIDER_MFA_TRUSTED",
        "OAUTH_PROVIDER_MFA_NOT_TRUSTED",
        "HANDOFF_TOKEN_ISSUED",
        "HANDOFF_TOKEN_CONSUMED",
        "HANDOFF_REPLAY_DETECTED",
        "HANDOFF_HOST_MISMATCH",
        # G.5.4 misc.
        "LOGOUT",
        "PASSWORD_CHANGED",
        "PASSWORD_RESET_REQUESTED",
        "PASSWORD_RESET_COMPLETED",
        "EMAIL_VERIFICATION_SENT",
        "EMAIL_VERIFIED",
        "ACCOUNT_LOCKED",
        "ACCOUNT_UNLOCKED",
    }
)


class AuditOutsideTransactionError(RuntimeError):
    pass


class UnknownAuditEventError(ValueError):
    pass


def audit_emit(
    event_type: str,
    *,
    actor_id: UUID | None,
    organization_id: UUID | None,
    object_kind: str | None = None,
    object_id: str | None = None,
    payload_before: dict[str, Any] | None = None,
    payload_after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    on_behalf_of_id: UUID | None = None,
) -> None:
    if event_type not in _KNOWN_EVENT_TYPES:
        raise UnknownAuditEventError(
            f"Unknown audit event_type {event_type!r}. Either fix the "
            f"call site, or register the new type in "
            f"apps.platform.audit.services._KNOWN_EVENT_TYPES and "
            f"amend G.5.2 in docs/guide.md."
        )

    if connection.in_atomic_block is False:
        raise AuditOutsideTransactionError(
            f"audit_emit({event_type!r}) called outside a transaction. "
            "Wrap the surrounding state change in `transaction.atomic()` "
            "so the audit row commits atomically with the state change."
        )

    event = AuditEvent(
        event_type=event_type,
        actor_id=actor_id,
        organization_id=organization_id,
        object_kind=object_kind,
        object_id=object_id,
        payload_before=payload_before,
        payload_after=payload_after,
        metadata=metadata,
        on_behalf_of_id=on_behalf_of_id,
    )

    if is_audit_recording_enabled():
        _buffer().append(event)
    else:
        logger.debug(
            "audit_emit stub: %s actor=%s org=%s object=%s/%s",
            event_type,
            actor_id,
            organization_id,
            object_kind,
            object_id,
        )
