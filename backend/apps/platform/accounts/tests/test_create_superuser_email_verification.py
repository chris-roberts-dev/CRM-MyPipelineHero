"""Tests for the M1 D7 Phase 1 createsuperuser ergonomics fix.

Verifies that ``UserManager.create_superuser`` auto-creates a
verified primary allauth ``EmailAddress`` row. Without this, the
first ``createsuperuser`` on a fresh deployment can't sign in
because settings include
``ACCOUNT_EMAIL_VERIFICATION = "mandatory"``.
"""

from __future__ import annotations

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model


@pytest.mark.django_db
class TestCreateSuperuserEmailVerification:
    def test_create_superuser_creates_verified_email_address(self) -> None:
        UserModel = get_user_model()
        user = UserModel.objects.create_superuser(
            email="bootstrap@example.test",
            password="boot-strap-pw-1234!",
        )

        email_row = EmailAddress.objects.get(user=user, email="bootstrap@example.test")
        assert email_row.verified is True
        assert email_row.primary is True

    def test_create_superuser_is_idempotent_for_email_address(self) -> None:
        """If ``create_superuser`` is somehow re-run (or another path
        creates the EmailAddress first), the helper should not
        duplicate-create."""
        UserModel = get_user_model()
        # First call creates user + EmailAddress.
        UserModel.objects.create_superuser(
            email="idem@example.test",
            password="idem-pw-1234!",
        )

        # Direct call to the helper a second time — simulates
        # re-running with an existing verified row.
        from apps.platform.accounts.utils import ensure_verified_email_address

        user = UserModel.objects.get(email="idem@example.test")
        created = ensure_verified_email_address(user)

        # Returns False on update path, no duplicate row.
        assert created is False
        assert (
            EmailAddress.objects.filter(user=user, email="idem@example.test").count()
            == 1
        )

    def test_create_regular_user_does_not_create_email_address(self) -> None:
        """``create_user`` (non-superuser) does NOT auto-verify.

        Regular users must go through the normal allauth email
        verification flow. The ergonomics fix is ONLY for the
        bootstrap-superuser case.
        """
        UserModel = get_user_model()
        user = UserModel.objects.create_user(
            email="regular@example.test",
            password="regular-pw-1234!",
        )
        assert EmailAddress.objects.filter(user=user).count() == 0
