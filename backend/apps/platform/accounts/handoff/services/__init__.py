"""Handoff services package (M1 D6).

Phase 1 — Signing-key lifecycle:
* create_handoff_signing_key
* promote_handoff_signing_key
* retire_handoff_signing_key
* emergency_rotate_handoff_signing_key
* active_handoff_signing_keys_ordered_by_created_desc (query helper)

Phase 2 — Token issue/consume:
* issue_handoff_token
* consume_handoff_token
* HandoffResult (return type)
"""

from __future__ import annotations

from apps.platform.accounts.handoff.results import HandoffResult
from apps.platform.accounts.handoff.services._consume import (
    consume_handoff_token,
)
from apps.platform.accounts.handoff.services._issue import (
    issue_handoff_token,
)
from apps.platform.accounts.handoff.services._keys import (
    active_handoff_signing_keys_ordered_by_created_desc,
    create_handoff_signing_key,
    emergency_rotate_handoff_signing_key,
    promote_handoff_signing_key,
    retire_handoff_signing_key,
)
from apps.platform.accounts.handoff.services.exceptions import (
    HandoffInvalidError,
    HandoffInvalidIssueParamError,
    HandoffSigningKeyAlreadyExistsError,
    HandoffSigningKeyAlreadyPromotedError,
    HandoffSigningKeyAlreadyRetiredError,
    HandoffSigningKeyError,
    HandoffSigningKeyInvalidIdError,
    HandoffSigningKeyNotFoundError,
    HandoffSigningKeyNotPromotedError,
    HandoffTokenError,
    InvalidHandoffActorError,
    NoActiveHandoffSigningKeyError,
    TooManyActiveHandoffSigningKeysError,
)

__all__ = [
    # Phase 1 services
    "active_handoff_signing_keys_ordered_by_created_desc",
    "create_handoff_signing_key",
    "emergency_rotate_handoff_signing_key",
    "promote_handoff_signing_key",
    "retire_handoff_signing_key",
    # Phase 2 services
    "consume_handoff_token",
    "issue_handoff_token",
    # Result type
    "HandoffResult",
    # Exceptions
    "HandoffInvalidError",
    "HandoffInvalidIssueParamError",
    "HandoffSigningKeyAlreadyExistsError",
    "HandoffSigningKeyAlreadyPromotedError",
    "HandoffSigningKeyAlreadyRetiredError",
    "HandoffSigningKeyError",
    "HandoffSigningKeyInvalidIdError",
    "HandoffSigningKeyNotFoundError",
    "HandoffSigningKeyNotPromotedError",
    "HandoffTokenError",
    "InvalidHandoffActorError",
    "NoActiveHandoffSigningKeyError",
    "TooManyActiveHandoffSigningKeysError",
]
