"""Typed exceptions for the handoff services (M1 D6)."""

from __future__ import annotations


class HandoffSigningKeyError(Exception):
    """Base for signing-key service exceptions."""


class HandoffSigningKeyInvalidIdError(HandoffSigningKeyError):
    """The supplied key_id doesn't match the required format.

    The format is enforced because key_id is used as the JWT ``kid``
    header and ends up in audit logs; arbitrary user input would
    create operational and log-hygiene problems.
    """


class HandoffSigningKeyAlreadyExistsError(HandoffSigningKeyError):
    """A HandoffSigningKey with this key_id already exists."""


class HandoffSigningKeyNotFoundError(HandoffSigningKeyError):
    """No HandoffSigningKey row with the supplied key_id."""


class HandoffSigningKeyAlreadyPromotedError(HandoffSigningKeyError):
    """promote_handoff_signing_key called on a key already promoted."""


class HandoffSigningKeyNotPromotedError(HandoffSigningKeyError):
    """retire_handoff_signing_key called on a never-promoted key.

    Retiring a never-promoted key would orphan it without a clear
    audit trail. If the operator really wants to discard a key that
    was created in error, they can manually delete the row.
    """


class HandoffSigningKeyAlreadyRetiredError(HandoffSigningKeyError):
    """retire_handoff_signing_key called on an already-retired key."""


class TooManyActiveHandoffSigningKeysError(HandoffSigningKeyError):
    """Refusing to create a third non-retired key.

    B.4.13.1: holding more than two non-retired keys is prohibited.
    """


class InvalidHandoffActorError(HandoffSigningKeyError):
    """The supplied actor is neither staff nor the system user.

    Key rotation is an operational action and requires a privileged
    actor. M1 D7's platform-admin UI will supply real staff users;
    until then, system-user actors are accepted for migrations and
    bootstrapping.
    """


# ---------------------------------------------------------------------------
# Phase 2 — Token issue/consume exceptions.
# ---------------------------------------------------------------------------


class HandoffTokenError(Exception):
    """Base for token issue/consume exceptions."""


class NoActiveHandoffSigningKeyError(HandoffTokenError):
    """Refusing to issue: no non-retired HandoffSigningKey exists.

    The platform admin must rotate in a new key before handoff tokens
    can be issued. Without an active signing key, no token can be
    cryptographically issued or verified.
    """


class HandoffInvalidIssueParamError(HandoffTokenError):
    """An issue parameter failed validation.

    Causes:
    - ``auth_method`` is not in the B.4.14 allowed set.
    - ``mfa_satisfied_at`` is in the future.
    - ``mfa_satisfied_at`` is absurdly stale (> 1 hour ago).
    - ``user_id`` / ``organization_id`` / ``membership_id`` do not
      reference an active membership.
    """


class HandoffInvalidError(HandoffTokenError):
    """Token consume failed validation.

    The ``reason`` attribute carries a stable code suitable for
    audit metadata and user-facing error pages. Values:

    * ``"expired"`` — JWT exp claim is in the past.
    * ``"invalid"`` — JWT structurally malformed or claim set incomplete.
    * ``"invalid_signature"`` — no active signing key verified the JWT.
    * ``"not_found_or_replayed"`` — Redis nonce missing.
    * ``"host_mismatch"`` — request host doesn't match the token's
      organization slug.
    * ``"membership_inactive"`` — Membership row no longer ACTIVE.
    * ``"organization_missing"`` — Organization referenced by token
      does not exist.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
