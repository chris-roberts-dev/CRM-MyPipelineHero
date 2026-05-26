"""Handoff services package (M1 D6).

Phase 1 — Signing-key lifecycle.
Phase 2 — Token issue/consume.
Phase 4B — Tenant session establishment.
Phase 5 — Token revocation on logout.
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
from apps.platform.accounts.handoff.services._revoke import (
    revoke_all_handoff_tokens_for_user,
)
from apps.platform.accounts.handoff.services._tenant_session import (
    SESSION_KEY_AUTH_METHOD,
    SESSION_KEY_AUTH_PROVIDER,
    SESSION_KEY_MEMBERSHIP_ID,
    SESSION_KEY_MFA_SATISFIED_AT,
    SESSION_KEY_ORGANIZATION_ID,
    establish_tenant_session,
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
    # Phase 1
    "active_handoff_signing_keys_ordered_by_created_desc",
    "create_handoff_signing_key",
    "emergency_rotate_handoff_signing_key",
    "promote_handoff_signing_key",
    "retire_handoff_signing_key",
    # Phase 2
    "consume_handoff_token",
    "issue_handoff_token",
    # Phase 4B
    "establish_tenant_session",
    "SESSION_KEY_ORGANIZATION_ID",
    "SESSION_KEY_MEMBERSHIP_ID",
    "SESSION_KEY_AUTH_METHOD",
    "SESSION_KEY_AUTH_PROVIDER",
    "SESSION_KEY_MFA_SATISFIED_AT",
    # Phase 5
    "revoke_all_handoff_tokens_for_user",
    # Result
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
