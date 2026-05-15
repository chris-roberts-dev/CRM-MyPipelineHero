"""Authentication-event audit service (M1 D4).

This is the single service-layer entry point used by allauth signal
handlers (in :mod:`apps.platform.accounts.signals`) to emit
authentication audit events. The signal handlers themselves contain
zero business logic; they translate allauth's signal payload into a
call to :func:`record_auth_event`, which owns the transaction
boundary and the actual ``audit_emit`` call.

**Why this layer exists**

The project rule (A.4.4) is that ``apps/*/services/`` is the sole
state-change boundary. ``audit_emit`` is a state change in the
audit-trail sense, and it requires an open ``transaction.atomic()``.
Allauth signals fire outside any service's atomic block, so each
signal handler needs *some* boundary. Rather than have every handler
open its own ``transaction.atomic()`` and call ``audit_emit`` inline
(which would scatter audit-emission logic across many files), we
funnel all of them through this one service.

**Signal handlers are exempt-equivalent.** They live in ``signals.py``,
not in ``services/``, so the service-discipline AST check
(``scripts/check_service_layer_discipline.py``) treats them like
views — they MUST NOT make ORM writes. The only call they make
into the platform is :func:`record_auth_event`, which IS in
``services/`` and owns the transaction.

**Failure isolation.** A failure inside ``record_auth_event`` MUST
NOT abort the originating auth flow. Allauth's signal dispatch is
synchronous; a raise propagates up. The function therefore swallows
``Exception`` after logging it, with the documented exception of
``AuditOutsideTransactionError`` and ``UnknownAuditEventError`` which
are programming errors and re-raise (these surface in tests, not in
production where the recording stub is off).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.platform.audit.services import (
    AuditOutsideTransactionError,
    UnknownAuditEventError,
    audit_emit,
)

logger = logging.getLogger(__name__)


def record_auth_event(
    *,
    event_type: str,
    actor_id: UUID | None,
    organization_id: UUID | None = None,
    object_kind: str | None = None,
    object_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit an authentication-related audit event from a signal handler.

    Owns its own ``transaction.atomic()`` boundary so allauth signal
    handlers can call it without holding a transaction. This is the
    only service in the codebase that is permitted to be invoked from
    a signal handler (A.4.4 documents the carve-out for audit
    fan-out).

    Args:
        event_type: Must be present in ``_KNOWN_EVENT_TYPES``. See
            B.4.19 for the catalog of authentication codes.
        actor_id: UUID of the User the event is *about*. For
            ``LOGIN_FAILED`` and ``ACCOUNT_LOCKED`` this may be None
            (e.g. credentials with no matching user) — pass None and
            put the attempted email in ``metadata``.
        organization_id: Always None for platform-tier auth events.
            Reserved for future per-tenant auth events (e.g. if a
            login is scoped to an org context).
        object_kind: Optional dotted model label.
        object_id: Optional stringified id of the affected object.
        metadata: Free-form metadata. Must NEVER contain:
            cleartext passwords, OAuth tokens, ID tokens, refresh
            tokens, authorization codes, TOTP secrets, recovery codes,
            CSRF tokens, session keys. Per B.4.19 + G.5.5.

    Raises:
        UnknownAuditEventError: registered as a programming error and
            re-raised. Indicates a typo in the signal handler.
        AuditOutsideTransactionError: re-raised. Indicates this
            function failed to open its own transaction — would
            be a Django/library bug.

    Behavior on any other exception: logged at WARNING and swallowed,
    so an audit-stub hiccup never breaks login.
    """
    try:
        with transaction.atomic():
            audit_emit(
                event_type,
                actor_id=actor_id,
                organization_id=organization_id,
                object_kind=object_kind,
                object_id=object_id,
                metadata=metadata,
            )
    except (UnknownAuditEventError, AuditOutsideTransactionError):
        raise
    except Exception:
        logger.warning(
            "record_auth_event failed for event_type=%s actor_id=%s; "
            "auth flow continues without audit record.",
            event_type,
            actor_id,
            exc_info=True,
        )
