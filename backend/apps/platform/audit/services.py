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

G.5.2 catalogs `MEMBER_INVITED` / `MEMBER_ACCEPTED_INVITE` for membership
creation and `ROLE_ASSIGNED` for role assignment. M1 D2 introduces two
codes not yet in the registry — `ORG_CREATED` and `MEMBERSHIP_CREATED`
— for the service-bootstrap flow (no invitation step). M1 D4 adds
`USER_REGISTERED` and the MFA lifecycle codes
(`MFA_ENROLLED`, `MFA_DISABLED`, `MFA_RECOVERY_CODES_REGENERATED`,
`MFA_RECOVERY_CODE_CONSUMED`). These additions will be folded into
G.5.2 during M2 audit work.
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


# ---------------------------------------------------------------------------
# AuditEvent value type (M1 stub; replaced by ORM model in M2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditEvent:
    """In-memory representation of an audit event.

    Mirrors the C.1.14 AuditEvent shape minus storage-only fields
    (id, schema_version). Test code reads this via
    :func:`captured_audit_events`; production code never touches it.
    """

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


# ---------------------------------------------------------------------------
# Recording buffer
# ---------------------------------------------------------------------------


_local = threading.local()


def is_audit_recording_enabled() -> bool:
    """True iff the audit stub should capture events to the in-memory buffer."""
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
    """Return audit events captured so far in this thread.

    Optional filters narrow the result. Used by tests to assert that
    a service emitted the expected events.

    Note: the buffer accumulates across the test session unless cleared.
    The :func:`reset_captured_audit_events` fixture in
    ``apps/platform/audit/conftest.py`` clears it between tests.
    """
    out = list(_buffer())
    if event_type is not None:
        out = [e for e in out if e.event_type == event_type]
    if organization_id is not None:
        out = [e for e in out if e.organization_id == organization_id]
    return out


def reset_captured_audit_events() -> None:
    """Clear the per-thread audit buffer. Test infrastructure only."""
    _local.buffer = []


# ---------------------------------------------------------------------------
# audit_emit — the public service-facing API
# ---------------------------------------------------------------------------


# Event codes the M1 stub recognizes. Listed here so a typo at a call
# site fails loudly rather than silently emitting an event nobody can
# search for in M2. New event types must be added here AND in G.5.2.
_KNOWN_EVENT_TYPES: frozenset[str] = frozenset(
    {
        # ---------------------------------------------------------------
        # M1 D2 additions (pending G.5.2 amendment).
        # ---------------------------------------------------------------
        "ORG_CREATED",
        "MEMBERSHIP_CREATED",
        # ---------------------------------------------------------------
        # M1 D4 additions (pending G.5.2 amendment).
        # ---------------------------------------------------------------
        "USER_REGISTERED",
        "MFA_ENROLLED",
        "MFA_DISABLED",
        "MFA_RECOVERY_CODES_REGENERATED",
        "MFA_RECOVERY_CODE_CONSUMED",
        # ---------------------------------------------------------------
        # G.5.2 Membership / RBAC.
        # ---------------------------------------------------------------
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
        # ---------------------------------------------------------------
        # G.5.2 Tenant lifecycle.
        # ---------------------------------------------------------------
        "TENANT_EXPORT_REQUESTED",
        "TENANT_EXPORT_ASSEMBLED",
        "TENANT_EXPORT_DOWNLOADED",
        "TENANT_DELETION_REQUESTED",
        "TENANT_DELETION_GRACE_STARTED",
        "TENANT_DELETION_EXECUTED",
        "TENANT_DELETION_CANCELLED",
        # ---------------------------------------------------------------
        # B.4.19 Authentication audit events.
        # ---------------------------------------------------------------
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
        # ---------------------------------------------------------------
        # G.5.4 categorization: LOGOUT, SESSION_*, ACCOUNT_*, PASSWORD_*.
        # These are listed by G.5.4 even though B.4.19 doesn't enumerate
        # every code; concrete codes registered here as we use them.
        # ---------------------------------------------------------------
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
    """Raised when ``audit_emit`` is called without an open transaction.

    Audit events MUST commit atomically with the state change they
    describe (G.5.3). The stub enforces this even before the partitioned
    storage layer exists, so service code that forgets to wrap a write
    in ``transaction.atomic`` fails the same way in M1 and M2.
    """


class UnknownAuditEventError(ValueError):
    """Raised when ``audit_emit`` is called with an event_type not in the
    known set. Either the caller has a typo, or the event type genuinely
    is new and needs to be added to ``_KNOWN_EVENT_TYPES`` (and G.5.2).
    """


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
    """Emit an audit event (G.5.3).

    Stub implementation: validates the call shape, ensures a
    transaction is open, and (if recording is enabled) appends the
    event to the in-memory buffer for test inspection. The real
    implementation lands in M2.

    Args:
        event_type: One of the codes in G.5.2 (or its M1 D2 / D4 extensions).
            Must be present in ``_KNOWN_EVENT_TYPES``.
        actor_id: UUID of the User performing the action. Use the
            System User when the action is system-triggered (C.2 says
            "system-triggered transitions attribute the actor to the
            System User").
        organization_id: UUID of the affected Organization, or None for
            platform-tier events (e.g. cross-tenant queries).
        object_kind: dotted model label, e.g. ``"platform_organizations.Organization"``.
        object_id: stringified primary key of the affected object.
        payload_before / payload_after: optional state snapshots.
            Masking is applied per G.5.5 in the M2 implementation.
        metadata: optional free-form metadata.
        on_behalf_of_id: UUID of the user being impersonated, if any
            (B.7).

    Raises:
        UnknownAuditEventError: ``event_type`` is not in the known set.
        AuditOutsideTransactionError: called without an open transaction.
    """
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
        # Production / staging without recording: log a thin breadcrumb
        # so we can confirm the call happened. The M2 implementation
        # replaces this with a real insert.
        logger.debug(
            "audit_emit stub: %s actor=%s org=%s object=%s/%s",
            event_type,
            actor_id,
            organization_id,
            object_kind,
            object_id,
        )
