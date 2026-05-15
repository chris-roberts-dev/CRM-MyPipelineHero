"""Tests for the register_local_user service (M1 D4).

Covers:
- happy path with verified user creation
- email-collision rejection (typed exception)
- password-policy rejection (Django validators)
- missing actor rejection
- USER_REGISTERED audit event emission and content
- atomicity: failure leaves no partial state
- password never appears in any captured audit payload
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.platform.accounts.services import (
    UserAlreadyExistsError,
    UserNotFoundError,
    register_local_user,
)
from apps.platform.audit.services import captured_audit_events


@pytest.fixture
def system_actor_id(db: Any) -> Any:
    """The seed_v1 System User id — the canonical bootstrap actor."""
    User = get_user_model()
    return User.objects.get(is_system=True).id


@pytest.mark.django_db
class TestRegisterLocalUser:
    def test_happy_path_creates_user(self, system_actor_id: Any) -> None:
        user = register_local_user(
            email="new-user@example.test",
            password="strong-password-12345!",
            actor_id=system_actor_id,
        )
        User = get_user_model()
        assert User.objects.filter(email="new-user@example.test").exists()
        assert user.email == "new-user@example.test"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_system is False
        assert user.password_changed_at is not None
        assert user.check_password("strong-password-12345!")

    def test_email_is_lowercased(self, system_actor_id: Any) -> None:
        user = register_local_user(
            email="Mixed.Case@Example.TEST",
            password="strong-password-12345!",
            actor_id=system_actor_id,
        )
        assert user.email == "mixed.case@example.test"

    def test_email_collision_raises(self, system_actor_id: Any) -> None:
        register_local_user(
            email="collision@example.test",
            password="strong-password-12345!",
            actor_id=system_actor_id,
        )
        with pytest.raises(UserAlreadyExistsError) as exc:
            register_local_user(
                email="collision@example.test",
                password="another-strong-password!",
                actor_id=system_actor_id,
            )
        assert exc.value.email == "collision@example.test"

    def test_email_collision_case_insensitive(self, system_actor_id: Any) -> None:
        register_local_user(
            email="case@example.test",
            password="strong-password-12345!",
            actor_id=system_actor_id,
        )
        with pytest.raises(UserAlreadyExistsError):
            register_local_user(
                email="CASE@EXAMPLE.test",
                password="another-strong-password!",
                actor_id=system_actor_id,
            )

    def test_password_policy_rejection_short(self, system_actor_id: Any) -> None:
        # 12-char minimum (B.5.2). Use one shorter.
        with pytest.raises(ValidationError):
            register_local_user(
                email="short@example.test",
                password="short",
                actor_id=system_actor_id,
            )

    def test_password_policy_rejection_common(self, system_actor_id: Any) -> None:
        with pytest.raises(ValidationError):
            register_local_user(
                email="common@example.test",
                password="password1234",
                actor_id=system_actor_id,
            )

    def test_invalid_email_shape_rejected(self, system_actor_id: Any) -> None:
        with pytest.raises(ValidationError):
            register_local_user(
                email="not-an-email",
                password="strong-password-12345!",
                actor_id=system_actor_id,
            )

    def test_missing_actor_raises(self, db: Any) -> None:
        import uuid

        with pytest.raises(UserNotFoundError):
            register_local_user(
                email="orphan@example.test",
                password="strong-password-12345!",
                actor_id=uuid.uuid4(),
            )

    def test_null_actor_raises(self, db: Any) -> None:
        with pytest.raises(ValueError):
            register_local_user(
                email="null-actor@example.test",
                password="strong-password-12345!",
                actor_id=None,  # type: ignore[arg-type]
            )

    def test_audit_event_emitted(self, system_actor_id: Any) -> None:
        user = register_local_user(
            email="audited@example.test",
            password="strong-password-12345!",
            actor_id=system_actor_id,
        )
        events = captured_audit_events(event_type="USER_REGISTERED")
        assert len(events) == 1
        event = events[0]
        assert event.actor_id == system_actor_id
        assert event.organization_id is None
        assert event.object_kind == "platform_accounts.User"
        assert event.object_id == str(user.id)
        assert event.payload_after is not None
        assert event.payload_after["email"] == "audited@example.test"
        assert event.payload_after["is_active"] is True
        assert event.payload_after["password_was_set"] is True

    def test_password_never_appears_in_audit_payload(
        self, system_actor_id: Any
    ) -> None:
        password = "this-cleartext-must-not-leak-987!"
        register_local_user(
            email="leak-check@example.test",
            password=password,
            actor_id=system_actor_id,
        )
        events = captured_audit_events(event_type="USER_REGISTERED")

        # Recursively walk every captured event payload looking for the
        # cleartext password. If it appears anywhere — payload_after,
        # metadata, even nested dicts — the test fails loudly.
        def _walk(obj: Any) -> None:
            if isinstance(obj, str):
                assert password not in obj, "cleartext password leaked into audit"
            elif isinstance(obj, dict):
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    _walk(v)

        for event in events:
            _walk(event.payload_after)
            _walk(event.payload_before)
            _walk(event.metadata)

    def test_atomicity_rolls_back_on_audit_failure(self, system_actor_id: Any) -> None:
        """If audit_emit raises mid-transaction, the User row is rolled back."""
        from apps.platform.audit.services import UnknownAuditEventError

        User = get_user_model()
        baseline = User.objects.count()

        with mock.patch(
            "apps.platform.accounts.services._register.audit_emit",
            side_effect=UnknownAuditEventError("simulated failure"),
        ):
            with pytest.raises(UnknownAuditEventError):
                register_local_user(
                    email="rollback@example.test",
                    password="strong-password-12345!",
                    actor_id=system_actor_id,
                )

        # No new user row should exist.
        assert User.objects.count() == baseline
        assert not User.objects.filter(email="rollback@example.test").exists()
