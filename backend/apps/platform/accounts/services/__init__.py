"""Account service layer (M1 D4).

Public API:

* :func:`register_local_user` — create a canonical ``User`` row for
  local-password authentication. Emits ``USER_REGISTERED``. Does NOT
  create a Membership; tenant membership is bootstrapped separately
  by :func:`apps.platform.organizations.services.assign_owner_membership`
  or, in M1 D5+, by the invite flow.
* :func:`record_auth_event` — the single service-layer entry point
  used by allauth signal handlers to emit auth-related audit events.
  Signal handlers themselves contain zero business logic; they
  delegate to this service so the "services are the sole state-change
  boundary" rule holds.

Service-layer rules (A.4.4):

* Functions accept primitive arguments (UUIDs, strings, decimals).
* Functions own their transaction boundaries via ``transaction.atomic(...)``.
* Audit events are emitted via :func:`apps.platform.audit.services.audit_emit`
  inside the same atomic boundary as the state change they describe.

Exceptions (defined in :mod:`apps.platform.accounts.services.exceptions`):

* :exc:`UserAlreadyExistsError` — email collision on registration.
* :exc:`UserNotFoundError` — caller referenced a nonexistent user.
"""

from __future__ import annotations

from apps.platform.accounts.services._audit import record_auth_event
from apps.platform.accounts.services._register import register_local_user
from apps.platform.accounts.services.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)

__all__ = [
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "record_auth_event",
    "register_local_user",
]
