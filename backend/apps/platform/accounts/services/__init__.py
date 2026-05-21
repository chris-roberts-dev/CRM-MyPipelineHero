"""Account service layer (M1 D4 + M1 D5).

Public API:

* :func:`register_local_user` (M1 D4) — create a canonical User row
  for local-password authentication.
* :func:`record_auth_event` (M1 D4) — single service entry for
  allauth signal handlers to emit auth audit events.
* :func:`resolve_external_user` (M1 D5) — resolve or link an
  OAuth/OIDC identity to a canonical User per B.4.6 / B.4.7.

Service-layer rules (A.4.4):

* Functions accept primitive arguments (UUIDs, strings, decimals).
* Functions own their transaction boundaries via ``transaction.atomic(...)``.
* Audit events are emitted via :func:`apps.platform.audit.services.audit_emit`
  inside the same atomic boundary as the state change they describe.

Exceptions (defined in :mod:`apps.platform.accounts.services.exceptions`):

M1 D4:
* :exc:`UserAlreadyExistsError` — email collision on registration.
* :exc:`UserNotFoundError` — caller referenced a nonexistent user.

M1 D5:
* :exc:`UserInactiveError` — matched user has is_active=False.
* :exc:`ProviderNotActiveError` — provider config is_active=False.
* :exc:`EmailNotVerifiedError` — provider didn't assert verified email.
* :exc:`EmailDomainNotAllowedError` — domain not in allowlist.
* :exc:`ConflictingExternalIdentityError` — existing different external
  identity for same provider.
* :exc:`NoExistingUserAndSelfRegistrationDisabledError` — no match and
  self-registration disabled.
* :exc:`LinkingNotAllowedError` — reserved for B.4.7 #5 (invite flow);
  not raised in M1 D5.
"""

from __future__ import annotations

from apps.platform.accounts.services._audit import record_auth_event
from apps.platform.accounts.services._register import register_local_user
from apps.platform.accounts.services._resolve_external import resolve_external_user
from apps.platform.accounts.services.exceptions import (
    ConflictingExternalIdentityError,
    EmailDomainNotAllowedError,
    EmailNotVerifiedError,
    LinkingNotAllowedError,
    NoExistingUserAndSelfRegistrationDisabledError,
    ProviderNotActiveError,
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
)

__all__ = [
    "ConflictingExternalIdentityError",
    "EmailDomainNotAllowedError",
    "EmailNotVerifiedError",
    "LinkingNotAllowedError",
    "NoExistingUserAndSelfRegistrationDisabledError",
    "ProviderNotActiveError",
    "UserAlreadyExistsError",
    "UserInactiveError",
    "UserNotFoundError",
    "record_auth_event",
    "register_local_user",
    "resolve_external_user",
]
