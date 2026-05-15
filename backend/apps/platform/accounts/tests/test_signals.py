"""Tests for allauth signal handlers (M1 D4).

Verifies that each handled allauth signal triggers the right audit
event with the right shape. Signal-handler logic is intentionally
thin (translate signal payload → service call), so the tests are
mostly contract assertions.
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from allauth.account.signals import (
    email_confirmed,
    password_changed,
    user_logged_in,
    user_logged_out,
    user_signed_up,
)
from django.contrib.auth.signals import user_login_failed

from apps.platform.audit.services import captured_audit_events


@pytest.fixture
def fake_request() -> Any:
    request = mock.MagicMock()
    request.path = "/test-path/"
    request.method = "POST"
    return request


@pytest.mark.django_db
class TestLoginSignals:
    def test_user_logged_in_emits_login_succeeded_and_local_password(
        self, user_verified_no_mfa: Any, fake_request: Any
    ) -> None:
        user_logged_in.send(
            sender=type(user_verified_no_mfa),
            request=fake_request,
            user=user_verified_no_mfa,
        )

        succeeded = captured_audit_events(event_type="LOGIN_SUCCEEDED")
        local = captured_audit_events(event_type="LOCAL_PASSWORD_LOGIN_SUCCEEDED")
        assert len(succeeded) == 1
        assert len(local) == 1
        assert succeeded[0].actor_id == user_verified_no_mfa.id
        assert local[0].actor_id == user_verified_no_mfa.id

    def test_user_login_failed_emits_with_attempted_email_no_password(
        self, fake_request: Any
    ) -> None:
        attempted_password = "the-secret-must-not-appear-89!"
        user_login_failed.send(
            sender=None,
            credentials={
                "login": "wrong@example.test",
                "password": attempted_password,
            },
            request=fake_request,
        )

        failed = captured_audit_events(event_type="LOGIN_FAILED")
        local_failed = captured_audit_events(event_type="LOCAL_PASSWORD_LOGIN_FAILED")
        assert len(failed) == 1
        assert len(local_failed) == 1

        # Email is captured.
        assert failed[0].metadata is not None
        assert failed[0].metadata["attempted_email"] == "wrong@example.test"

        # Password is NEVER captured anywhere.
        def _walk(obj: Any) -> None:
            if isinstance(obj, str):
                assert attempted_password not in obj
            elif isinstance(obj, dict):
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, (list, tuple)):
                for v in obj:
                    _walk(v)

        for event in failed + local_failed:
            _walk(event.metadata)
            _walk(event.payload_after)
            _walk(event.payload_before)

    def test_user_logged_out_emits_logout(
        self, user_verified_no_mfa: Any, fake_request: Any
    ) -> None:
        user_logged_out.send(
            sender=type(user_verified_no_mfa),
            request=fake_request,
            user=user_verified_no_mfa,
        )

        events = captured_audit_events(event_type="LOGOUT")
        assert len(events) == 1
        assert events[0].actor_id == user_verified_no_mfa.id


@pytest.mark.django_db
class TestLifecycleSignals:
    def test_user_signed_up_emits_user_registered(
        self, user_verified_no_mfa: Any, fake_request: Any
    ) -> None:
        user_signed_up.send(
            sender=type(user_verified_no_mfa),
            request=fake_request,
            user=user_verified_no_mfa,
        )

        events = captured_audit_events(event_type="USER_REGISTERED")
        # Should include the signup-driven emission (the service path
        # was not called here; this is the signal-fallback case).
        assert any(e.actor_id == user_verified_no_mfa.id for e in events)

    def test_password_changed_emits(
        self, user_verified_no_mfa: Any, fake_request: Any
    ) -> None:
        password_changed.send(
            sender=type(user_verified_no_mfa),
            request=fake_request,
            user=user_verified_no_mfa,
        )

        events = captured_audit_events(event_type="PASSWORD_CHANGED")
        assert len(events) == 1
        assert events[0].actor_id == user_verified_no_mfa.id

    def test_email_confirmed_emits(
        self, user_verified_no_mfa: Any, fake_request: Any
    ) -> None:
        from allauth.account.models import EmailAddress

        email_addr = EmailAddress.objects.filter(user=user_verified_no_mfa).first()
        email_confirmed.send(
            sender=EmailAddress,
            request=fake_request,
            email_address=email_addr,
        )

        events = captured_audit_events(event_type="EMAIL_VERIFIED")
        assert len(events) == 1
        assert events[0].actor_id == user_verified_no_mfa.id


@pytest.mark.django_db
class TestMfaSignals:
    """Direct invocation of allauth.mfa signals.

    These test our handler shape; the end-to-end MFA test suite
    exercises the real allauth flow that emits these signals.
    """

    def test_authenticator_added_totp_emits_mfa_enrolled(
        self, user_with_totp: Any, fake_request: Any
    ) -> None:
        # user_with_totp fixture already enrolled TOTP, which triggered
        # the signal. Buffer is reset between tests (audit conftest),
        # so capture is empty by entry — re-fire to test the path.
        from allauth.mfa.models import Authenticator
        from allauth.mfa.signals import authenticator_added

        auth_row = Authenticator.objects.filter(
            user=user_with_totp, type=Authenticator.Type.TOTP
        ).first()

        authenticator_added.send(
            sender=Authenticator,
            request=fake_request,
            user=user_with_totp,
            authenticator=auth_row,
        )

        events = captured_audit_events(event_type="MFA_ENROLLED")
        assert len(events) >= 1
        assert any(e.actor_id == user_with_totp.id for e in events)

    def test_authenticator_added_recovery_codes_emits_regenerated(
        self, user_with_totp_and_recovery: Any, fake_request: Any
    ) -> None:
        from allauth.mfa.models import Authenticator
        from allauth.mfa.signals import authenticator_added

        auth_row = Authenticator.objects.filter(
            user=user_with_totp_and_recovery,
            type=Authenticator.Type.RECOVERY_CODES,
        ).first()

        authenticator_added.send(
            sender=Authenticator,
            request=fake_request,
            user=user_with_totp_and_recovery,
            authenticator=auth_row,
        )

        events = captured_audit_events(event_type="MFA_RECOVERY_CODES_REGENERATED")
        assert len(events) >= 1

    def test_authenticator_removed_emits_mfa_disabled(
        self, user_with_totp: Any, fake_request: Any
    ) -> None:
        from allauth.mfa.models import Authenticator
        from allauth.mfa.signals import authenticator_removed

        auth_row = Authenticator.objects.filter(
            user=user_with_totp, type=Authenticator.Type.TOTP
        ).first()

        authenticator_removed.send(
            sender=Authenticator,
            request=fake_request,
            user=user_with_totp,
            authenticator=auth_row,
        )

        events = captured_audit_events(event_type="MFA_DISABLED")
        assert len(events) == 1
        assert events[0].actor_id == user_with_totp.id
