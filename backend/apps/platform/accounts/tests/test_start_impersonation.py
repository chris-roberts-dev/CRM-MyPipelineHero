"""Tests for start_impersonation service (M1 D7 Phase 4)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from apps.platform.accounts.impersonation.models import ImpersonationSession
from apps.platform.accounts.impersonation.services import (
    ImpersonationActorNotStaffError,
    ImpersonationAlreadyActiveError,
    ImpersonationMembershipInvalidError,
    ImpersonationReasonRequiredError,
    ImpersonationSelfTargetError,
    ImpersonationTargetInvalidError,
    start_impersonation,
)
from apps.platform.audit.services import captured_audit_events
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)

_VALID_REASON = "Investigating support ticket #1234"


@pytest.fixture
def staff_admin(user_factory: Any) -> Any:
    user = user_factory(email="admin-svc@example.test")
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def regular_target(user_factory: Any) -> Any:
    return user_factory(email="target-svc@example.test")


@pytest.fixture
def org_and_membership(
    regular_target: Any,
) -> tuple[Organization, Membership]:
    org = Organization.objects.create(
        slug="svc-org",
        name="Service Test Org",
        primary_contact_email="svc@example.test",
    )
    membership = Membership.objects.create(
        user=regular_target,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return org, membership


@pytest.mark.django_db
class TestStartImpersonationHappyPath:
    def test_returns_session_row(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        session = start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=regular_target.id,
            organization_id=org.id,
            membership_id=membership.id,
            reason=_VALID_REASON,
        )
        assert isinstance(session, ImpersonationSession)
        assert session.admin_user_id == staff_admin.id
        assert session.target_user_id == regular_target.id
        assert session.organization_id == org.id
        assert session.membership_id == membership.id
        assert session.reason == _VALID_REASON
        assert session.ended_at is None
        assert session.is_active is True

    def test_emits_audit_event(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=regular_target.id,
            organization_id=org.id,
            membership_id=membership.id,
            reason=_VALID_REASON,
        )
        events = captured_audit_events(event_type="IMPERSONATION_STARTED")
        assert len(events) == 1
        evt = events[0]
        assert evt.actor_id == staff_admin.id
        assert evt.organization_id == org.id
        assert evt.on_behalf_of_id == regular_target.id
        assert evt.metadata is not None
        assert evt.metadata["target_user_id"] == str(regular_target.id)
        # Reason TEXT must NOT be in metadata.
        assert "reason" not in evt.metadata
        assert _VALID_REASON not in str(evt.metadata)

    def test_reason_is_stripped(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        session = start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=regular_target.id,
            organization_id=org.id,
            membership_id=membership.id,
            reason="   investigating customer issue  ",
        )
        assert session.reason == "investigating customer issue"


@pytest.mark.django_db
class TestStartImpersonationValidation:
    def test_self_target_raises_and_audits_denied(
        self, staff_admin: Any, org_and_membership: tuple[Organization, Membership]
    ) -> None:
        org, membership = org_and_membership
        with pytest.raises(ImpersonationSelfTargetError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=staff_admin.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )
        events = captured_audit_events(event_type="IMPERSONATION_DENIED")
        assert any(
            e.metadata and e.metadata.get("reason_code") == "self_target"
            for e in events
        )

    def test_short_reason_raises_and_audits(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        with pytest.raises(ImpersonationReasonRequiredError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=regular_target.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason="short",
            )
        events = captured_audit_events(event_type="IMPERSONATION_DENIED")
        assert any(
            e.metadata and e.metadata.get("reason_code") == "reason_required"
            for e in events
        )

    def test_empty_reason_raises(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        with pytest.raises(ImpersonationReasonRequiredError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=regular_target.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason="",
            )

    def test_actor_not_found_raises_and_audits(
        self,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        random_admin_id = uuid4()
        with pytest.raises(ImpersonationActorNotStaffError):
            start_impersonation(
                admin_user_id=random_admin_id,
                target_user_id=regular_target.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_actor_not_staff_raises(
        self,
        user_factory: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        non_staff = user_factory(email="not-staff@example.test")
        org, membership = org_and_membership
        with pytest.raises(ImpersonationActorNotStaffError):
            start_impersonation(
                admin_user_id=non_staff.id,
                target_user_id=regular_target.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_target_not_found_raises(
        self,
        staff_admin: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        random_target_id = uuid4()
        with pytest.raises(ImpersonationTargetInvalidError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=random_target_id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_target_inactive_raises(
        self,
        staff_admin: Any,
        user_factory: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        inactive_target = user_factory(email="inactive@example.test")
        inactive_target.is_active = False
        inactive_target.save()
        # Re-anchor membership to the inactive user for shape correctness.
        membership.user = inactive_target
        membership.save()
        with pytest.raises(ImpersonationTargetInvalidError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=inactive_target.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_target_is_staff_raises(
        self,
        staff_admin: Any,
        user_factory: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        staff_target = user_factory(email="staff-target@example.test")
        staff_target.is_staff = True
        staff_target.save()
        membership.user = staff_target
        membership.save()
        with pytest.raises(ImpersonationTargetInvalidError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=staff_target.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_target_is_system_raises(
        self,
        staff_admin: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        from django.contrib.auth import get_user_model

        system_user = get_user_model().objects.get(is_system=True)
        org, membership = org_and_membership
        # Membership has to belong to the system user for this case.
        membership.user = system_user
        membership.save()
        with pytest.raises(ImpersonationTargetInvalidError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=system_user.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_membership_not_found_raises(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, _ = org_and_membership
        random_membership_id = uuid4()
        with pytest.raises(ImpersonationMembershipInvalidError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=regular_target.id,
                organization_id=org.id,
                membership_id=random_membership_id,
                reason=_VALID_REASON,
            )

    def test_membership_wrong_org_raises(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        _, membership = org_and_membership
        other_org = Organization.objects.create(
            slug="other-org",
            name="Other Org",
            primary_contact_email="other@example.test",
        )
        # Membership belongs to org_and_membership.org, but we pass other_org.id.
        with pytest.raises(ImpersonationMembershipInvalidError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=regular_target.id,
                organization_id=other_org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_membership_not_active_raises(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        membership.status = MembershipStatus.SUSPENDED
        membership.save()
        with pytest.raises(ImpersonationMembershipInvalidError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=regular_target.id,
                organization_id=org.id,
                membership_id=membership.id,
                reason=_VALID_REASON,
            )

    def test_admin_with_existing_active_session_raises(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
        user_factory: Any,
    ) -> None:
        org, membership = org_and_membership
        # First session: succeeds.
        start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=regular_target.id,
            organization_id=org.id,
            membership_id=membership.id,
            reason=_VALID_REASON,
        )
        # Second attempt for same admin → ImpersonationAlreadyActiveError.
        other_target = user_factory(email="other@example.test")
        other_membership = Membership.objects.create(
            user=other_target,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        with pytest.raises(ImpersonationAlreadyActiveError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=other_target.id,
                organization_id=org.id,
                membership_id=other_membership.id,
                reason=_VALID_REASON,
            )

    def test_denied_audit_emitted_when_already_active(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
        user_factory: Any,
    ) -> None:
        org, membership = org_and_membership
        start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=regular_target.id,
            organization_id=org.id,
            membership_id=membership.id,
            reason=_VALID_REASON,
        )
        other_target = user_factory(email="other-2@example.test")
        other_membership = Membership.objects.create(
            user=other_target,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        with pytest.raises(ImpersonationAlreadyActiveError):
            start_impersonation(
                admin_user_id=staff_admin.id,
                target_user_id=other_target.id,
                organization_id=org.id,
                membership_id=other_membership.id,
                reason=_VALID_REASON,
            )
        events = captured_audit_events(event_type="IMPERSONATION_DENIED")
        assert any(
            e.metadata
            and e.metadata.get("reason_code") == "admin_already_impersonating"
            for e in events
        )
