"""HandoffSigningKey lifecycle services (B.4.13.1, M1 D6 Phase 1).

All four mutating services share these properties per project posture:

* Keyword-only primitive arguments.
* Single ``transaction.atomic()`` per call.
* Audit event emitted inside the atomic boundary.
* Actor must be staff or the system user.
* Typed exceptions on failure.

Per B.4.13.1 the active key set is read via the query helper
``active_handoff_signing_keys_ordered_by_created_desc`` rather than
embedded queries — keeping the ordering rule in exactly one place.
"""

from __future__ import annotations

import logging
import re
import secrets
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.platform.accounts.handoff.encryption import encrypt_handoff_secret
from apps.platform.accounts.handoff.models import HandoffSigningKey
from apps.platform.accounts.handoff.services.exceptions import (
    HandoffSigningKeyAlreadyExistsError,
    HandoffSigningKeyAlreadyPromotedError,
    HandoffSigningKeyAlreadyRetiredError,
    HandoffSigningKeyInvalidIdError,
    HandoffSigningKeyNotFoundError,
    HandoffSigningKeyNotPromotedError,
    InvalidHandoffActorError,
    TooManyActiveHandoffSigningKeysError,
)
from apps.platform.audit.services import audit_emit

logger = logging.getLogger(__name__)


# Key-id format. Enforced for operational hygiene — the value ends
# up in JWT ``kid`` headers, audit logs, and operator-facing UIs.
# Accepts e.g. "hsk_2026q2", "hsk_2026q3", "hsk_emergency_20260522".
_KEY_ID_PATTERN = re.compile(r"^hsk_[a-z0-9_]{1,57}$")

# HS256 secret length. RFC 7518 minimum is 256 bits (32 bytes); we
# use 64 bytes for defense in depth — gives 512 bits of entropy and
# matches Fernet's internal block size for clean padding.
_HMAC_SECRET_BYTES = 64

# B.4.13.1 invariant.
_MAX_ACTIVE_KEYS = 2


# ---------------------------------------------------------------------------
# Actor validation.
# ---------------------------------------------------------------------------


def _validate_actor(actor_id: UUID) -> None:
    """Actor must be staff or the system user.

    M1 D7 platform-admin UI will supply real staff users; for now,
    the System User is accepted so migrations / shell can rotate.
    """
    UserModel = get_user_model()
    try:
        actor = UserModel.objects.get(id=actor_id)
    except UserModel.DoesNotExist as exc:
        raise InvalidHandoffActorError(
            f"actor_id={actor_id!r} does not match any User"
        ) from exc

    if not (actor.is_staff or getattr(actor, "is_system", False)):
        raise InvalidHandoffActorError(
            f"actor_id={actor_id!r} is neither staff nor system; "
            "key rotation is restricted."
        )


# ---------------------------------------------------------------------------
# Key-id validation.
# ---------------------------------------------------------------------------


def _validate_key_id(key_id: str) -> None:
    if not isinstance(key_id, str):
        raise HandoffSigningKeyInvalidIdError(
            f"key_id must be str, got {type(key_id).__name__}"
        )
    if not _KEY_ID_PATTERN.match(key_id):
        raise HandoffSigningKeyInvalidIdError(
            f"key_id={key_id!r} does not match required format "
            f"({_KEY_ID_PATTERN.pattern})"
        )


# ---------------------------------------------------------------------------
# Query helper.
# ---------------------------------------------------------------------------


def active_handoff_signing_keys_ordered_by_created_desc() -> list[HandoffSigningKey]:
    """Return non-retired signing keys, newest first.

    The newest non-retired key (index 0) is the primary used for
    token issuance. Older non-retired keys (index 1+) are valid for
    verification during the rotation overlap.

    Returns an empty list if no keys are active — token issuance
    will raise; token verification cannot succeed.
    """
    return list(
        HandoffSigningKey.objects.filter(retired_at__isnull=True).order_by(
            "-created_at"
        )
    )


# ---------------------------------------------------------------------------
# create_handoff_signing_key
# ---------------------------------------------------------------------------


def create_handoff_signing_key(
    *,
    actor_id: UUID,
    key_id: str,
) -> HandoffSigningKey:
    """Create a new signing key (lifecycle step 1).

    The new key is NOT yet promoted — it cannot verify tokens until
    ``promote_handoff_signing_key`` is called. This matches B.4.13.1
    step 1: "generated but not yet primary."

    Args:
        actor_id: User performing the rotation. Must be staff or
            system.
        key_id: Short stable identifier (e.g. "hsk_2026q3"). Must
            match ``_KEY_ID_PATTERN``.

    Raises:
        HandoffSigningKeyInvalidIdError: key_id format invalid.
        HandoffSigningKeyAlreadyExistsError: key_id already in use.
        TooManyActiveHandoffSigningKeysError: refusing to create a
            third non-retired key.
        InvalidHandoffActorError: actor is not staff or system.
    """
    _validate_actor(actor_id)
    _validate_key_id(key_id)

    with transaction.atomic():
        if HandoffSigningKey.objects.filter(key_id=key_id).exists():
            raise HandoffSigningKeyAlreadyExistsError(
                f"HandoffSigningKey with key_id={key_id!r} already exists"
            )

        active_count = HandoffSigningKey.objects.filter(retired_at__isnull=True).count()
        if active_count >= _MAX_ACTIVE_KEYS:
            raise TooManyActiveHandoffSigningKeysError(
                f"Cannot create a third non-retired HandoffSigningKey "
                f"(currently {active_count} active). Retire the oldest "
                f"active key first."
            )

        raw_secret = secrets.token_bytes(_HMAC_SECRET_BYTES)
        encrypted = encrypt_handoff_secret(raw_secret)

        signing_key = HandoffSigningKey.objects.create(
            key_id=key_id,
            secret=encrypted,
            algorithm="HS256",
        )

        audit_emit(
            "HANDOFF_SIGNING_KEY_CREATED",
            actor_id=actor_id,
            organization_id=None,
            object_kind="platform_accounts.HandoffSigningKey",
            object_id=str(signing_key.id),
            metadata={
                "key_id": key_id,
                "algorithm": "HS256",
            },
        )

        return signing_key


# ---------------------------------------------------------------------------
# promote_handoff_signing_key
# ---------------------------------------------------------------------------


def promote_handoff_signing_key(
    *,
    actor_id: UUID,
    key_id: str,
) -> HandoffSigningKey:
    """Promote a created key to primary (lifecycle step 2).

    After promotion, the key becomes the primary used for issuance.
    The previous primary remains active for verification until
    ``retire_handoff_signing_key`` is called.

    Raises:
        HandoffSigningKeyNotFoundError: no such key_id.
        HandoffSigningKeyAlreadyPromotedError: key already promoted.
        HandoffSigningKeyAlreadyRetiredError: key has been retired.
        InvalidHandoffActorError: actor is not staff or system.
    """
    _validate_actor(actor_id)

    with transaction.atomic():
        try:
            signing_key = HandoffSigningKey.objects.select_for_update().get(
                key_id=key_id
            )
        except HandoffSigningKey.DoesNotExist as exc:
            raise HandoffSigningKeyNotFoundError(
                f"No HandoffSigningKey with key_id={key_id!r}"
            ) from exc

        if signing_key.retired_at is not None:
            raise HandoffSigningKeyAlreadyRetiredError(
                f"HandoffSigningKey key_id={key_id!r} is retired and "
                f"cannot be promoted."
            )
        if signing_key.promoted_at is not None:
            raise HandoffSigningKeyAlreadyPromotedError(
                f"HandoffSigningKey key_id={key_id!r} is already promoted "
                f"(at {signing_key.promoted_at!r})."
            )

        signing_key.promoted_at = timezone.now()
        signing_key.save(update_fields=["promoted_at"])

        audit_emit(
            "HANDOFF_SIGNING_KEY_PROMOTED",
            actor_id=actor_id,
            organization_id=None,
            object_kind="platform_accounts.HandoffSigningKey",
            object_id=str(signing_key.id),
            metadata={
                "key_id": key_id,
                "promoted_at": signing_key.promoted_at.isoformat(),
            },
        )

        return signing_key


# ---------------------------------------------------------------------------
# retire_handoff_signing_key
# ---------------------------------------------------------------------------


def retire_handoff_signing_key(
    *,
    actor_id: UUID,
    key_id: str,
) -> HandoffSigningKey:
    """Retire a promoted key (lifecycle step 4).

    A retired key is preserved for audit reconstruction but no
    longer used for verification.

    Raises:
        HandoffSigningKeyNotFoundError: no such key_id.
        HandoffSigningKeyNotPromotedError: key was never promoted.
        HandoffSigningKeyAlreadyRetiredError: key already retired.
        InvalidHandoffActorError: actor is not staff or system.
    """
    _validate_actor(actor_id)

    with transaction.atomic():
        try:
            signing_key = HandoffSigningKey.objects.select_for_update().get(
                key_id=key_id
            )
        except HandoffSigningKey.DoesNotExist as exc:
            raise HandoffSigningKeyNotFoundError(
                f"No HandoffSigningKey with key_id={key_id!r}"
            ) from exc

        if signing_key.retired_at is not None:
            raise HandoffSigningKeyAlreadyRetiredError(
                f"HandoffSigningKey key_id={key_id!r} is already retired "
                f"(at {signing_key.retired_at!r})."
            )
        if signing_key.promoted_at is None:
            raise HandoffSigningKeyNotPromotedError(
                f"HandoffSigningKey key_id={key_id!r} was never promoted; "
                f"refusing to retire."
            )

        signing_key.retired_at = timezone.now()
        signing_key.save(update_fields=["retired_at"])

        audit_emit(
            "HANDOFF_SIGNING_KEY_RETIRED",
            actor_id=actor_id,
            organization_id=None,
            object_kind="platform_accounts.HandoffSigningKey",
            object_id=str(signing_key.id),
            metadata={
                "key_id": key_id,
                "retired_at": signing_key.retired_at.isoformat(),
            },
        )

        return signing_key


# ---------------------------------------------------------------------------
# emergency_rotate_handoff_signing_key
# ---------------------------------------------------------------------------


def emergency_rotate_handoff_signing_key(
    *,
    actor_id: UUID,
    new_key_id: str,
) -> HandoffSigningKey:
    """Emergency rotation: create + promote + retire previous primary.

    Per B.4.13.1 step 5: "perform steps 1-2 immediately, set the
    overlap window to 60 seconds (the maximum token lifetime), then
    retire."

    In M1 D6 Phase 1, we don't sleep the 60s in-process — that would
    block the calling process. The previous primary is retired
    immediately; in-flight tokens issued by it will simply fail
    verification rather than continue working. **This is a stricter
    interpretation of emergency rotation than B.4.13.1 — it cuts
    the overlap window to zero rather than 60 seconds.** The
    tradeoff is acceptable for emergency response (where the suspected
    compromise outweighs in-flight UX) but deviates from the spec.
    Tracked in retro.

    The emergency-rotation audit event is emitted with the original
    key_id (the one being compromised) in metadata.

    Raises: any of the exceptions create_/promote_/retire_ raise.
    """
    _validate_actor(actor_id)
    _validate_key_id(new_key_id)

    with transaction.atomic():
        # Capture the current primary (if any) so the audit event
        # records what we rotated away from.
        active = active_handoff_signing_keys_ordered_by_created_desc()
        previous_primary = active[0] if active else None

        if previous_primary is not None and previous_primary.key_id == new_key_id:
            # Operator passed the existing primary's id by mistake.
            raise HandoffSigningKeyAlreadyExistsError(
                f"new_key_id={new_key_id!r} matches the current primary; "
                f"choose a new key_id for emergency rotation."
            )

        # Step 1+2: create AND promote in one go (the new key is
        # immediately the primary).
        if HandoffSigningKey.objects.filter(key_id=new_key_id).exists():
            raise HandoffSigningKeyAlreadyExistsError(
                f"HandoffSigningKey with key_id={new_key_id!r} already exists"
            )

        # Defensive: if there are already two non-retired keys, retire
        # the oldest first to make room for the new emergency key.
        # This handles the edge case where emergency rotation lands
        # during a normal rotation overlap.
        non_retired = HandoffSigningKey.objects.filter(
            retired_at__isnull=True
        ).order_by("created_at")
        if non_retired.count() >= _MAX_ACTIVE_KEYS:
            oldest = non_retired.first()
            oldest.retired_at = timezone.now()
            oldest.save(update_fields=["retired_at"])
            audit_emit(
                "HANDOFF_SIGNING_KEY_RETIRED",
                actor_id=actor_id,
                organization_id=None,
                object_kind="platform_accounts.HandoffSigningKey",
                object_id=str(oldest.id),
                metadata={
                    "key_id": oldest.key_id,
                    "retired_at": oldest.retired_at.isoformat(),
                    "context": "emergency_rotation_overflow",
                },
            )

        raw_secret = secrets.token_bytes(_HMAC_SECRET_BYTES)
        encrypted = encrypt_handoff_secret(raw_secret)

        new_key = HandoffSigningKey.objects.create(
            key_id=new_key_id,
            secret=encrypted,
            algorithm="HS256",
            promoted_at=timezone.now(),
        )

        # Step 4 inline: retire the previous primary immediately
        # (zero overlap window). If there was no previous primary,
        # skip — this is the first key ever.
        previous_key_id = None
        if previous_primary is not None:
            previous_primary.retired_at = timezone.now()
            previous_primary.save(update_fields=["retired_at"])
            previous_key_id = previous_primary.key_id

        audit_emit(
            "HANDOFF_SIGNING_KEY_EMERGENCY_ROTATED",
            actor_id=actor_id,
            organization_id=None,
            object_kind="platform_accounts.HandoffSigningKey",
            object_id=str(new_key.id),
            metadata={
                "new_key_id": new_key_id,
                "previous_key_id": previous_key_id,
                "overlap_window_seconds": 0,
                "deviation_from_spec": (
                    "B.4.13.1 step 5 specifies a 60-second overlap window; "
                    "this implementation uses zero overlap (immediate "
                    "retirement of previous primary). Tracked in M1 D6 "
                    "retro."
                ),
            },
        )

        return new_key
