"""Tests for handoff signing key management views (M1 D7 Phase 3)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from django.test import Client

from apps.platform.accounts.handoff.models import HandoffSigningKey
from apps.platform.accounts.handoff.services import (
    create_handoff_signing_key,
    promote_handoff_signing_key,
)
from apps.platform.audit.services import captured_audit_events


@pytest.fixture
def staff_user(user_verified_with_totp: Any) -> Any:
    user_verified_with_totp.is_staff = True
    user_verified_with_totp.save()
    return user_verified_with_totp


@pytest.fixture
def staff_client(client: Client, staff_user: Any) -> Client:
    client.force_login(staff_user)
    return client


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def pending_key(system_actor_id: UUID) -> HandoffSigningKey:
    return create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_pending")


@pytest.fixture
def primary_key(system_actor_id: UUID) -> HandoffSigningKey:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_primary")
    return promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_primary")


# ---------------------------------------------------------------------------
# List view.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSigningKeysList:
    def test_empty_state_renders_warning(self, staff_client: Client) -> None:
        response = staff_client.get("/platform/signing-keys/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "No active signing key" in body

    def test_lists_pending_key(
        self, staff_client: Client, pending_key: HandoffSigningKey
    ) -> None:
        response = staff_client.get("/platform/signing-keys/")
        body = response.content.decode()
        assert "hsk_pending" in body
        assert "Pending" in body
        assert "Promote" in body

    def test_lists_primary_key(
        self, staff_client: Client, primary_key: HandoffSigningKey
    ) -> None:
        response = staff_client.get("/platform/signing-keys/")
        body = response.content.decode()
        assert "hsk_primary" in body
        assert "Primary" in body
        assert "Emergency rotate" in body

    def test_create_link_visible(self, staff_client: Client) -> None:
        response = staff_client.get("/platform/signing-keys/")
        body = response.content.decode()
        assert "/platform/signing-keys/create/" in body


# ---------------------------------------------------------------------------
# Create view.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSigningKeyCreate:
    def test_get_renders_form(self, staff_client: Client) -> None:
        response = staff_client.get("/platform/signing-keys/create/")
        assert response.status_code == 200
        assert b"Create signing key" in response.content
        assert b'name="key_id"' in response.content

    def test_post_creates_key_and_redirects(self, staff_client: Client) -> None:
        response = staff_client.post(
            "/platform/signing-keys/create/",
            data={"key_id": "hsk_new_key"},
        )
        assert response.status_code == 302
        assert response["Location"] == "/platform/signing-keys/"
        assert HandoffSigningKey.objects.filter(key_id="hsk_new_key").exists()

    def test_post_audit_emitted_with_staff_actor(
        self, staff_client: Client, staff_user: Any
    ) -> None:
        staff_client.post(
            "/platform/signing-keys/create/",
            data={"key_id": "hsk_audit_test"},
        )
        events = captured_audit_events(event_type="HANDOFF_SIGNING_KEY_CREATED")
        assert len(events) >= 1
        latest = events[-1]
        assert latest.actor_id == staff_user.id

    def test_post_empty_key_id_returns_error(self, staff_client: Client) -> None:
        response = staff_client.post(
            "/platform/signing-keys/create/",
            data={"key_id": ""},
        )
        assert response.status_code == 400
        assert b"Key ID is required" in response.content

    def test_post_duplicate_key_id_returns_error(
        self, staff_client: Client, pending_key: HandoffSigningKey
    ) -> None:
        response = staff_client.post(
            "/platform/signing-keys/create/",
            data={"key_id": pending_key.key_id},
        )
        assert response.status_code == 400
        assert b"already exists" in response.content

    def test_post_invalid_key_id_format_returns_error(
        self, staff_client: Client
    ) -> None:
        # Service requires hsk_ prefix; "bad_id" lacks it.
        response = staff_client.post(
            "/platform/signing-keys/create/",
            data={"key_id": "bad_id_no_prefix"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Promote view.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSigningKeyPromote:
    def test_get_renders_confirmation(
        self, staff_client: Client, pending_key: HandoffSigningKey
    ) -> None:
        response = staff_client.get(
            f"/platform/signing-keys/{pending_key.key_id}/promote/"
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert "Promote signing key" in body
        assert pending_key.key_id in body
        assert "Confirm promote" in body

    def test_get_404_for_unknown_key(self, staff_client: Client) -> None:
        response = staff_client.get("/platform/signing-keys/hsk_nonexistent/promote/")
        assert response.status_code == 404

    def test_post_promotes_and_redirects(
        self, staff_client: Client, pending_key: HandoffSigningKey
    ) -> None:
        response = staff_client.post(
            f"/platform/signing-keys/{pending_key.key_id}/promote/"
        )
        assert response.status_code == 302
        assert response["Location"] == "/platform/signing-keys/"
        pending_key.refresh_from_db()
        assert pending_key.promoted_at is not None

    def test_post_already_promoted_returns_error(
        self, staff_client: Client, primary_key: HandoffSigningKey
    ) -> None:
        response = staff_client.post(
            f"/platform/signing-keys/{primary_key.key_id}/promote/"
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Retire view.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSigningKeyRetire:
    def test_get_renders_confirmation(
        self, staff_client: Client, primary_key: HandoffSigningKey
    ) -> None:
        response = staff_client.get(
            f"/platform/signing-keys/{primary_key.key_id}/retire/"
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert "Retire signing key" in body
        assert primary_key.key_id in body

    def test_post_retires_promoted_key(
        self, staff_client: Client, primary_key: HandoffSigningKey
    ) -> None:
        response = staff_client.post(
            f"/platform/signing-keys/{primary_key.key_id}/retire/"
        )
        assert response.status_code == 302
        primary_key.refresh_from_db()
        assert primary_key.retired_at is not None

    def test_post_never_promoted_returns_error(
        self, staff_client: Client, pending_key: HandoffSigningKey
    ) -> None:
        response = staff_client.post(
            f"/platform/signing-keys/{pending_key.key_id}/retire/"
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Emergency rotate view.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSigningKeyEmergencyRotate:
    def test_get_renders_destructive_confirmation(
        self, staff_client: Client, primary_key: HandoffSigningKey
    ) -> None:
        response = staff_client.get("/platform/signing-keys/emergency-rotate/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "Emergency rotate" in body
        assert "Destructive action" in body
        assert primary_key.key_id in body  # Current primary visible.

    def test_get_when_no_primary_shows_first_key_message(
        self, staff_client: Client
    ) -> None:
        response = staff_client.get("/platform/signing-keys/emergency-rotate/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "No current primary key" in body

    def test_post_rotates_and_creates_new_primary(
        self,
        staff_client: Client,
        primary_key: HandoffSigningKey,
    ) -> None:
        response = staff_client.post(
            "/platform/signing-keys/emergency-rotate/",
            data={"new_key_id": "hsk_emergency_replacement"},
        )
        assert response.status_code == 302
        assert response["Location"] == "/platform/signing-keys/"

        # Old key is retired.
        primary_key.refresh_from_db()
        assert primary_key.retired_at is not None

        # New key exists and is promoted (non-retired).
        new_key = HandoffSigningKey.objects.get(key_id="hsk_emergency_replacement")
        assert new_key.promoted_at is not None
        assert new_key.retired_at is None

    def test_post_empty_new_key_id_returns_error(
        self, staff_client: Client, primary_key: HandoffSigningKey
    ) -> None:
        response = staff_client.post(
            "/platform/signing-keys/emergency-rotate/",
            data={"new_key_id": ""},
        )
        assert response.status_code == 400
        assert b"required" in response.content
        # Old key NOT retired.
        primary_key.refresh_from_db()
        assert primary_key.retired_at is None

    def test_post_duplicate_new_key_id_returns_error(
        self,
        staff_client: Client,
        primary_key: HandoffSigningKey,
    ) -> None:
        """Using the current primary's key_id as new_key_id is
        rejected — service raises HandoffSigningKeyAlreadyExistsError."""
        response = staff_client.post(
            "/platform/signing-keys/emergency-rotate/",
            data={"new_key_id": primary_key.key_id},
        )
        assert response.status_code == 400
        # Old key NOT retired.
        primary_key.refresh_from_db()
        assert primary_key.retired_at is None

    def test_post_invalid_new_key_id_format_returns_error(
        self, staff_client: Client, primary_key: HandoffSigningKey
    ) -> None:
        response = staff_client.post(
            "/platform/signing-keys/emergency-rotate/",
            data={"new_key_id": "no_prefix"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Access control sanity.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSigningKeyAccessControl:
    def test_create_requires_staff(
        self, client: Client, user_verified_with_totp: Any
    ) -> None:
        client.force_login(user_verified_with_totp)
        response = client.post(
            "/platform/signing-keys/create/", data={"key_id": "hsk_x"}
        )
        assert response.status_code == 403
        assert not HandoffSigningKey.objects.filter(key_id="hsk_x").exists()

    def test_promote_requires_staff(
        self,
        client: Client,
        user_verified_with_totp: Any,
        pending_key: HandoffSigningKey,
    ) -> None:
        client.force_login(user_verified_with_totp)
        response = client.post(f"/platform/signing-keys/{pending_key.key_id}/promote/")
        assert response.status_code == 403
        pending_key.refresh_from_db()
        assert pending_key.promoted_at is None

    def test_emergency_rotate_requires_staff(
        self,
        client: Client,
        user_verified_with_totp: Any,
        primary_key: HandoffSigningKey,
    ) -> None:
        client.force_login(user_verified_with_totp)
        response = client.post(
            "/platform/signing-keys/emergency-rotate/",
            data={"new_key_id": "hsk_attempt"},
        )
        assert response.status_code == 403
        # Old key NOT retired; new key NOT created.
        primary_key.refresh_from_db()
        assert primary_key.retired_at is None
        assert not HandoffSigningKey.objects.filter(key_id="hsk_attempt").exists()
