"""Tests for UserImpersonateView (M1 D7 Phase 5)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from django.test import Client

from apps.platform.accounts.handoff.services._keys import (
    create_handoff_signing_key,
    promote_handoff_signing_key,
)
from apps.platform.accounts.impersonation.models import ImpersonationSession
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)

_VALID_REASON = "Investigating impersonation view test"


@pytest.fixture
def system_actor_id(db: Any) -> UUID:
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(is_system=True).id


@pytest.fixture
def signing_key_ready(system_actor_id: UUID) -> None:
    create_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5view")
    promote_handoff_signing_key(actor_id=system_actor_id, key_id="hsk_p5view")


@pytest.fixture
def staff_admin(user_verified_with_totp: Any) -> Any:
    """Staff admin WITH TOTP enrolled.

    The RequireMfaEnrollmentMiddleware redirects staff users without
    TOTP to /accounts/2fa/totp/activate/, which fails platform-console
    tests with 302 instead of 200. Use the verified-with-TOTP fixture
    as the base, then flip is_staff=True. This matches the pattern
    Phase 3's signing-key tests use.
    """
    user_verified_with_totp.is_staff = True
    user_verified_with_totp.save()
    return user_verified_with_totp


@pytest.fixture
def staff_client(client: Client, staff_admin: Any) -> Client:
    client.force_login(staff_admin)
    return client


@pytest.fixture
def target_user(user_factory: Any) -> Any:
    return user_factory(email="view-target@example.test")


@pytest.fixture
def org_and_membership(
    target_user: Any,
) -> tuple[Organization, Membership]:
    org = Organization.objects.create(
        slug="viewp5org",
        name="View P5 Org",
        primary_contact_email="vp5@example.test",
    )
    membership = Membership.objects.create(
        user=target_user,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return org, membership


@pytest.mark.django_db
class TestUserImpersonateViewGet:
    def test_get_renders_confirmation_with_memberships(
        self,
        staff_client: Client,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        response = staff_client.get(f"/platform/users/{target_user.id}/impersonate/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "Start impersonation" in body
        assert target_user.email in body
        assert org.name in body
        assert str(membership.id) in body

    def test_get_shows_message_when_no_active_memberships(
        self,
        staff_client: Client,
        user_factory: Any,
    ) -> None:
        no_memb = user_factory(email="no-memb@example.test")
        response = staff_client.get(f"/platform/users/{no_memb.id}/impersonate/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "no active memberships" in body.lower()

    def test_get_404_for_unknown_user(self, staff_client: Client) -> None:
        from uuid import uuid4

        response = staff_client.get(f"/platform/users/{uuid4()}/impersonate/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestUserImpersonateViewPost:
    def test_post_starts_session_and_renders_handoff_form(
        self,
        staff_client: Client,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        response = staff_client.post(
            f"/platform/users/{target_user.id}/impersonate/",
            data={
                "membership_id": str(membership.id),
                "reason": _VALID_REASON,
            },
        )
        assert response.status_code == 200
        body = response.content.decode()
        # Auto-POST form renders.
        assert f"{org.slug}.mph.local" in body
        assert "/handoff/" in body
        # ImpersonationSession row exists.
        assert ImpersonationSession.objects.filter(
            target_user=target_user, organization=org, ended_at__isnull=True
        ).exists()

    def test_post_short_reason_returns_error(
        self,
        staff_client: Client,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        response = staff_client.post(
            f"/platform/users/{target_user.id}/impersonate/",
            data={
                "membership_id": str(membership.id),
                "reason": "short",
            },
        )
        assert response.status_code == 400
        assert not ImpersonationSession.objects.filter(target_user=target_user).exists()

    def test_post_missing_membership_returns_error(
        self,
        staff_client: Client,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        response = staff_client.post(
            f"/platform/users/{target_user.id}/impersonate/",
            data={"reason": _VALID_REASON},
        )
        assert response.status_code == 400

    def test_post_invalid_target_staff_returns_error(
        self,
        staff_client: Client,
        signing_key_ready: None,
        user_factory: Any,
    ) -> None:
        other_staff = user_factory(email="other-staff@example.test")
        other_staff.is_staff = True
        other_staff.save()
        org = Organization.objects.create(
            slug="stafftargetorg",
            name="Staff Target Org",
            primary_contact_email="staff@example.test",
        )
        membership = Membership.objects.create(
            user=other_staff,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        response = staff_client.post(
            f"/platform/users/{other_staff.id}/impersonate/",
            data={
                "membership_id": str(membership.id),
                "reason": _VALID_REASON,
            },
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestImpersonationLogView:
    def test_get_shows_active_sessions(
        self,
        staff_client: Client,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        # Create a session via the impersonate view.
        org, membership = org_and_membership
        staff_client.post(
            f"/platform/users/{target_user.id}/impersonate/",
            data={
                "membership_id": str(membership.id),
                "reason": _VALID_REASON,
            },
        )
        response = staff_client.get("/platform/impersonation/")
        assert response.status_code == 200
        body = response.content.decode()
        assert target_user.email in body
        assert "Active sessions" in body

    def test_get_with_no_sessions_shows_empty_message(
        self, staff_client: Client
    ) -> None:
        response = staff_client.get("/platform/impersonation/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "No active impersonation sessions" in body


@pytest.mark.django_db
class TestEndImpersonationFromConsoleView:
    def test_post_ends_session(
        self,
        staff_client: Client,
        signing_key_ready: None,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
    ) -> None:
        from apps.platform.accounts.impersonation.services import (
            start_impersonation,
        )

        org, membership = org_and_membership
        session = start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            reason=_VALID_REASON,
        )

        response = staff_client.post(f"/platform/impersonation/{session.id}/end/")
        assert response.status_code == 302
        assert response["Location"] == "/platform/impersonation/"
        session.refresh_from_db()
        assert session.ended_at is not None

    def test_post_already_ended_returns_error(
        self,
        staff_client: Client,
        target_user: Any,
        org_and_membership: tuple[Organization, Membership],
        staff_admin: Any,
    ) -> None:
        from apps.platform.accounts.impersonation.models import (
            ImpersonationEndReason,
        )
        from apps.platform.accounts.impersonation.services import (
            end_impersonation,
            start_impersonation,
        )

        org, membership = org_and_membership
        session = start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=target_user.id,
            organization_id=org.id,
            membership_id=membership.id,
            reason=_VALID_REASON,
        )
        end_impersonation(
            session_id=session.id,
            ended_by_user_id=staff_admin.id,
            end_reason=ImpersonationEndReason.ADMIN_ENDED,
        )

        response = staff_client.post(f"/platform/impersonation/{session.id}/end/")
        assert response.status_code == 400
