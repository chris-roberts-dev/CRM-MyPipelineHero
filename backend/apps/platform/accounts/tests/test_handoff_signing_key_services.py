"""Tests for HandoffSigningKey lifecycle services (M1 D6 Phase 1).

Coverage:
* Fernet encryption round-trip (model layer)
* create_handoff_signing_key validation + audit emission
* promote_handoff_signing_key state transitions + audit
* retire_handoff_signing_key state transitions + audit
* emergency_rotate_handoff_signing_key full flow
* active_handoff_signing_keys_ordered_by_created_desc ordering
* "two non-retired max" invariant
* actor validation (staff / system / neither)
* __repr__ does not leak the encrypted secret
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model

from apps.platform.accounts.handoff.encryption import (
    HandoffSecretDecryptionError,
    decrypt_handoff_secret,
    encrypt_handoff_secret,
)
from apps.platform.accounts.handoff.models import HandoffSigningKey
from apps.platform.accounts.handoff.services import (
    HandoffSigningKeyAlreadyExistsError,
    HandoffSigningKeyAlreadyPromotedError,
    HandoffSigningKeyAlreadyRetiredError,
    HandoffSigningKeyInvalidIdError,
    HandoffSigningKeyNotFoundError,
    HandoffSigningKeyNotPromotedError,
    InvalidHandoffActorError,
    TooManyActiveHandoffSigningKeysError,
    active_handoff_signing_keys_ordered_by_created_desc,
    create_handoff_signing_key,
    emergency_rotate_handoff_signing_key,
    promote_handoff_signing_key,
    retire_handoff_signing_key,
)
from apps.platform.audit.services import captured_audit_events

# ---------------------------------------------------------------------------
# Actor fixtures.
# ---------------------------------------------------------------------------


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    UserModel = get_user_model()
    return UserModel.objects.get(is_system=True).id


@pytest.fixture
def staff_actor_id(db: Any) -> UUID:
    UserModel = get_user_model()
    user = UserModel.objects.create(
        email="staff-handoff@example.test",
        is_active=True,
        is_staff=True,
    )
    user.set_unusable_password()
    user.save()
    return user.id


@pytest.fixture
def non_staff_actor_id(db: Any, user_factory: Any) -> UUID:
    user = user_factory(email="non-staff@example.test")
    return user.id


# ---------------------------------------------------------------------------
# Fernet encryption round-trip.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFernetEncryption:
    def test_encrypt_decrypt_round_trip(self) -> None:
        plaintext = b"\x00\x01\x02 ABC \xff\xfe" * 8
        ciphertext = encrypt_handoff_secret(plaintext)
        assert isinstance(ciphertext, str)
        assert ciphertext != plaintext.decode("latin-1", errors="ignore")
        recovered = decrypt_handoff_secret(ciphertext)
        assert recovered == plaintext

    def test_encrypt_rejects_non_bytes(self) -> None:
        with pytest.raises(TypeError):
            encrypt_handoff_secret("a string")  # type: ignore[arg-type]

    def test_decrypt_rejects_non_str(self) -> None:
        with pytest.raises(TypeError):
            decrypt_handoff_secret(b"bytes not str")  # type: ignore[arg-type]

    def test_decrypt_with_wrong_key_raises(self, settings: Any) -> None:
        plaintext = b"a secret"
        ciphertext = encrypt_handoff_secret(plaintext)
        # Override the master key — decryption should fail.
        settings.HANDOFF_KEY_ENCRYPTION_KEY = Fernet.generate_key().decode()
        with pytest.raises(HandoffSecretDecryptionError):
            decrypt_handoff_secret(ciphertext)

    def test_decrypt_with_tampered_ciphertext_raises(self) -> None:
        ciphertext = encrypt_handoff_secret(b"a secret")
        # Mangle a character.
        tampered = ciphertext[:-1] + ("A" if ciphertext[-1] != "A" else "B")
        with pytest.raises(HandoffSecretDecryptionError):
            decrypt_handoff_secret(tampered)


# ---------------------------------------------------------------------------
# create_handoff_signing_key
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateHandoffSigningKey:
    def test_creates_with_valid_key_id_and_system_actor(
        self, system_actor_id: UUID
    ) -> None:
        sk = create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_2026q2")
        assert sk.key_id == "hsk_2026q2"
        assert sk.promoted_at is None
        assert sk.retired_at is None
        assert sk.algorithm == "HS256"
        assert sk.secret  # ciphertext present
        assert sk.secret != ""

    def test_creates_with_staff_actor(self, staff_actor_id: UUID) -> None:
        sk = create_handoff_signing_key(actor_id=staff_actor_id, key_id="hsk_2026q2")
        assert sk.key_id == "hsk_2026q2"

    def test_rejects_non_staff_non_system_actor(self, non_staff_actor_id: UUID) -> None:
        with pytest.raises(InvalidHandoffActorError):
            create_handoff_signing_key(actor_id=non_staff_actor_id, key_id="hsk_2026q2")

    def test_rejects_unknown_actor(self, db: Any) -> None:
        from uuid import uuid4

        with pytest.raises(InvalidHandoffActorError):
            create_handoff_signing_key(actor_id=uuid4(), key_id="hsk_2026q2")

    def test_rejects_invalid_key_id_format(self, system_actor_id: UUID) -> None:
        for bad in ["", "no_prefix", "hsk_", "hsk_BAD", "hsk_with spaces"]:
            with pytest.raises(HandoffSigningKeyInvalidIdError):
                create_handoff_signing_key(actor_id=system_actor_id, key_id=bad)

    def test_rejects_duplicate_key_id(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_dup")
        with pytest.raises(HandoffSigningKeyAlreadyExistsError):
            create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_dup")

    def test_refuses_third_non_retired_key(self, system_actor_id: UUID) -> None:
        # Two active keys is the limit.
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_a")
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_b")
        with pytest.raises(TooManyActiveHandoffSigningKeysError):
            create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_c")

    def test_emits_created_audit_event(self, system_actor_id: UUID) -> None:
        sk = create_handoff_signing_key(
            actor_id=system_actor_id, key_id="hsk_audit_test"
        )
        events = captured_audit_events(event_type="HANDOFF_SIGNING_KEY_CREATED")
        assert len(events) == 1
        evt = events[0]
        assert evt.actor_id == system_actor_id
        assert evt.object_id == str(sk.id)
        assert evt.metadata is not None
        assert evt.metadata["key_id"] == "hsk_audit_test"
        assert evt.metadata["algorithm"] == "HS256"

    def test_secret_is_encrypted_round_trippable(self, system_actor_id: UUID) -> None:
        sk = create_handoff_signing_key(
            actor_id=system_actor_id, key_id="hsk_decrypt_test"
        )
        # Stored ciphertext is not the raw bytes.
        plaintext = decrypt_handoff_secret(sk.secret)
        assert len(plaintext) == 64  # _HMAC_SECRET_BYTES


# ---------------------------------------------------------------------------
# promote_handoff_signing_key
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPromoteHandoffSigningKey:
    def test_promotes_pending_key(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p1")
        sk = promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p1")
        assert sk.promoted_at is not None
        assert sk.retired_at is None

    def test_rejects_unknown_key(self, system_actor_id: UUID) -> None:
        with pytest.raises(HandoffSigningKeyNotFoundError):
            promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_missing")

    def test_rejects_already_promoted(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p2")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p2")
        with pytest.raises(HandoffSigningKeyAlreadyPromotedError):
            promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p2")

    def test_rejects_retired_key(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p3")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p3")
        retire_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p3")
        with pytest.raises(HandoffSigningKeyAlreadyRetiredError):
            promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p3")

    def test_emits_promoted_audit_event(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_pa")
        sk = promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_pa")
        events = captured_audit_events(event_type="HANDOFF_SIGNING_KEY_PROMOTED")
        assert len(events) == 1
        evt = events[0]
        assert evt.object_id == str(sk.id)
        assert evt.metadata is not None
        assert evt.metadata["key_id"] == "hsk_pa"


# ---------------------------------------------------------------------------
# retire_handoff_signing_key
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRetireHandoffSigningKey:
    def test_retires_promoted_key(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r1")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r1")
        sk = retire_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r1")
        assert sk.retired_at is not None

    def test_rejects_never_promoted(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r2")
        with pytest.raises(HandoffSigningKeyNotPromotedError):
            retire_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r2")

    def test_rejects_already_retired(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r3")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r3")
        retire_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r3")
        with pytest.raises(HandoffSigningKeyAlreadyRetiredError):
            retire_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_r3")

    def test_emits_retired_audit_event(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_ra")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_ra")
        sk = retire_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_ra")
        events = captured_audit_events(event_type="HANDOFF_SIGNING_KEY_RETIRED")
        # The emergency-rotation overflow path also emits RETIRED, so
        # filter by object_id.
        matching = [e for e in events if e.object_id == str(sk.id)]
        assert len(matching) == 1
        assert matching[0].metadata is not None
        assert matching[0].metadata["key_id"] == "hsk_ra"


# ---------------------------------------------------------------------------
# emergency_rotate_handoff_signing_key
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEmergencyRotate:
    def test_with_existing_primary_retires_it(self, system_actor_id: UUID) -> None:
        # Set up an existing primary.
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_old")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_old")

        new_key = emergency_rotate_handoff_signing_key(
            actor_id=system_actor_id, new_key_id="hsk_emerg"
        )

        old = HandoffSigningKey.objects.get(key_id="hsk_old")
        assert old.retired_at is not None
        assert new_key.promoted_at is not None
        assert new_key.retired_at is None

    def test_first_ever_key_no_previous_to_retire(self, system_actor_id: UUID) -> None:
        # No existing keys.
        assert not HandoffSigningKey.objects.exists()
        new_key = emergency_rotate_handoff_signing_key(
            actor_id=system_actor_id, new_key_id="hsk_first_emerg"
        )
        assert new_key.promoted_at is not None

    def test_emits_emergency_rotated_event(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_x")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_x")
        emergency_rotate_handoff_signing_key(
            actor_id=system_actor_id, new_key_id="hsk_y"
        )
        events = captured_audit_events(
            event_type="HANDOFF_SIGNING_KEY_EMERGENCY_ROTATED"
        )
        assert len(events) == 1
        evt = events[0]
        assert evt.metadata is not None
        assert evt.metadata["new_key_id"] == "hsk_y"
        assert evt.metadata["previous_key_id"] == "hsk_x"
        assert evt.metadata["overlap_window_seconds"] == 0

    def test_with_two_active_retires_oldest_first(self, system_actor_id: UUID) -> None:
        """Edge case: emergency rotation lands mid-normal-rotation."""
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_a")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_a")
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_b")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_b")

        emergency_rotate_handoff_signing_key(
            actor_id=system_actor_id, new_key_id="hsk_emerg2"
        )

        a = HandoffSigningKey.objects.get(key_id="hsk_a")
        b = HandoffSigningKey.objects.get(key_id="hsk_b")
        emerg = HandoffSigningKey.objects.get(key_id="hsk_emerg2")
        assert a.retired_at is not None
        assert b.retired_at is not None
        assert emerg.retired_at is None
        assert emerg.promoted_at is not None

    def test_rejects_new_key_id_matching_current_primary(
        self, system_actor_id: UUID
    ) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_same")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_same")
        with pytest.raises(HandoffSigningKeyAlreadyExistsError):
            emergency_rotate_handoff_signing_key(
                actor_id=system_actor_id, new_key_id="hsk_same"
            )


# ---------------------------------------------------------------------------
# active_handoff_signing_keys_ordered_by_created_desc
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestActiveKeysOrdering:
    def test_returns_empty_when_no_keys(self, db: Any) -> None:
        assert active_handoff_signing_keys_ordered_by_created_desc() == []

    def test_returns_newest_first(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_old")
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_new")
        keys = active_handoff_signing_keys_ordered_by_created_desc()
        assert len(keys) == 2
        # Newest first.
        assert keys[0].key_id == "hsk_new"
        assert keys[1].key_id == "hsk_old"

    def test_excludes_retired(self, system_actor_id: UUID) -> None:
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_keep")
        create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_gone")
        promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_gone")
        retire_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_gone")
        keys = active_handoff_signing_keys_ordered_by_created_desc()
        assert len(keys) == 1
        assert keys[0].key_id == "hsk_keep"


# ---------------------------------------------------------------------------
# __repr__ does not leak secret.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReprDoesNotLeakSecret:
    def test_repr_excludes_secret(self, system_actor_id: UUID) -> None:
        sk = create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_repr")
        rendered = repr(sk)
        assert sk.secret not in rendered
        # And the ciphertext starts with "gAAAAA" (Fernet's version prefix
        # base64-encoded). Make sure that doesn't appear either.
        assert "gAAAAA" not in rendered
        assert sk.key_id in rendered

    def test_str_excludes_secret(self, system_actor_id: UUID) -> None:
        sk = create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_str")
        rendered = str(sk)
        assert sk.secret not in rendered
        assert "gAAAAA" not in rendered
