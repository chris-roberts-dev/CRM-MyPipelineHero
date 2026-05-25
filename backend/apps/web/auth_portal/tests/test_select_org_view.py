"""Tests for SelectOrgView (M1 D6 Phase 4B, B.4.15)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from django.test import Client
from django.utils import timezone

from apps.platform.accounts.handoff.services import (
    create_handoff_signing_key,
    promote_handoff_signing_key,
)
from apps.platform.accounts.signals_mfa import SESSION_KEY_MFA_SATISFIED_AT
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def primary_signing_key(system_actor_id: UUID) -> Any:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_phase4b_primary")
    return promote_handoff_signing_key(
        actor_id=system_actor_id, key_id="hsk_phase4b_primary"
    )


def _login_with_mfa(client: Client, user: Any) -> None:
    client.force_login(user)
    session = client.session
    session[SESSION_KEY_MFA_SATISFIED_AT] = (
        timezone.now() - timedelta(seconds=10)
    ).isoformat()
    session.save()


@pytest.mark.django_db
class TestNoActiveAccess:
    def test_no_memberships_renders_no_access_page(
        self, client: Client, user_verified_with_totp: Any
    ) -> None:
        _login_with_mfa(client, user_verified_with_totp)
        response = client.get("/select-org/")
        assert response.status_code == 200
        assert b"No active access" in response.content


@pytest.mark.django_db
class TestSingleMembershipAutoAdvance:
    def test_one_membership_auto_renders_handoff_form(
        self,
        client: Client,
        user_verified_with_totp: Any,
        primary_signing_key: Any,
    ) -> None:
        org = Organization.objects.create(
            slug="autoadv",
            name="AutoAdvance Inc",
            primary_contact_email="contact@autoadv.test",
        )
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )

        _login_with_mfa(client, user_verified_with_totp)
        response = client.get("/select-org/")

        assert response.status_code == 200
        # Form action points at the tenant subdomain.
        assert b"autoadv.mph.local/handoff/" in response.content
        # Auto-submit script present.
        assert b"document.getElementById('handoff-form').submit()" in response.content


@pytest.mark.django_db
class TestMultipleMembershipsRendersPicker:
    def test_two_memberships_renders_picker_cards(
        self,
        client: Client,
        user_verified_with_totp: Any,
        primary_signing_key: Any,
    ) -> None:
        org_a = Organization.objects.create(
            slug="orga",
            name="Org A",
            primary_contact_email="a@example.test",
        )
        org_b = Organization.objects.create(
            slug="orgb",
            name="Org B",
            primary_contact_email="b@example.test",
        )
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_a,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            user=user_verified_with_totp,
            organization=org_b,
            status=MembershipStatus.ACTIVE,
        )

        _login_with_mfa(client, user_verified_with_totp)
        response = client.get("/select-org/")

        assert response.status_code == 200
        assert b"Org A" in response.content
        assert b"Org B" in response.content


@pytest.mark.django_db
class TestStaffPicker:
    def test_staff_with_no_memberships_sees_picker(
        self,
        client: Client,
        user_verified_with_totp: Any,
        primary_signing_key: Any,
    ) -> None:
        user_verified_with_totp.is_staff = True
        user_verified_with_totp.save()

        _login_with_mfa(client, user_verified_with_totp)
        response = client.get("/select-org/")

        assert response.status_code == 200
        # Platform console link visible for staff.
        assert b"platform console" in response.content
