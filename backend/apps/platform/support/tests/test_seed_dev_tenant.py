"""Tests for the seed_dev_tenant management command (M1 D4 update).

Verifies:
- Existing behavior: org + user + membership + owner role created.
- M1 D4 addition: verified primary EmailAddress row created for the
  admin user.
- Idempotency: re-running the command does not duplicate the
  EmailAddress.
- --reset: when the admin user is dropped, the EmailAddress row is
  CASCADE-deleted (no explicit cleanup needed).
"""

from __future__ import annotations

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.platform.organizations.models import Membership, Organization
from apps.platform.rbac.models import MembershipRole, Role


@pytest.mark.django_db
class TestSeedDevTenant:
    def test_initial_run_creates_verified_email_address(self) -> None:
        call_command("seed_dev_tenant")

        User = get_user_model()
        admin = User.objects.get(email="admin@mph.local")
        addr = EmailAddress.objects.get(user=admin, email="admin@mph.local")
        assert addr.verified is True
        assert addr.primary is True

    def test_idempotent_email_address_on_rerun(self) -> None:
        call_command("seed_dev_tenant")
        call_command("seed_dev_tenant")

        User = get_user_model()
        admin = User.objects.get(email="admin@mph.local")
        # Exactly one EmailAddress row.
        assert (
            EmailAddress.objects.filter(user=admin, email="admin@mph.local").count()
            == 1
        )

    def test_reset_drops_email_address_via_cascade(self) -> None:
        call_command("seed_dev_tenant")

        User = get_user_model()
        admin_before = User.objects.get(email="admin@mph.local")
        assert EmailAddress.objects.filter(user=admin_before).exists()

        call_command("seed_dev_tenant", "--reset")
        call_command("seed_dev_tenant")

        # User row was dropped and recreated. The new user's
        # EmailAddress is fresh.
        admin_after = User.objects.get(email="admin@mph.local")
        addr = EmailAddress.objects.get(user=admin_after)
        assert addr.verified is True

    def test_creates_org_user_membership_owner_role(self) -> None:
        call_command("seed_dev_tenant")

        org = Organization.objects.get(slug="demo")
        User = get_user_model()
        admin = User.objects.get(email="admin@mph.local")
        membership = Membership.objects.get(user=admin, organization=org)
        owner_role = Role.objects.get(organization=org, code="owner")
        assert MembershipRole.objects.filter(
            membership=membership, role=owner_role
        ).exists()
