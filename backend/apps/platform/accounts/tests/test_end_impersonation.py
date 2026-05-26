"""Tests for end_impersonation service (M1 D7 Phase 4)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from apps.platform.accounts.impersonation.models import (
    ImpersonationEndReason,
    ImpersonationSession,
)
from apps.platform.accounts.impersonation.services import (
    ImpersonationSessionAlreadyEndedError,
    ImpersonationSessionNotFoundError,
    end_impersonation,
    start_impersonation,
)
from apps.platform.audit.services import captured_audit_events
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)

_VALID_REASON = "Investigating support ticket for ending tests"


@pytest.fixture
def staff_admin(user_factory: Any) -> Any:
    user = user_factory(email="admin-end@example.test")
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def regular_target(user_factory: Any) -> Any:
    return user_factory(email="target-end@example.test")


@pytest.fixture
def session(
    staff_admin: Any,
    regular_target: Any,
    user_factory: Any,
) -> ImpersonationSession:
    org = Organization.objects.create(
        slug="end-org",
        name="End Test Org",
        primary_contact_email="end@example.test",
    )
    membership = Membership.objects.create(
        user=regular_target,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return start_impersonation(
        admin_user_id=staff_admin.id,
        target_user_id=regular_target.id,
        organization_id=org.id,
        membership_id=membership.id,
        reason=_VALID_REASON,
    )


@pytest.mark.django_db
class TestEndImpersonationHappyPath:
    def test_closes_session_and_returns(
        self, session: ImpersonationSession, staff_admin: Any
    ) -> None:
        result = end_impersonation(
            session_id=session.id,
            ended_by_user_id=staff_admin.id,
        )
        assert result.id == session.id
        assert result.ended_at is not None
        assert result.ended_by_user_id == staff_admin.id
        assert result.end_reason == ImpersonationEndReason.ADMIN_ENDED
        assert result.is_active is False

    def test_emits_audit_event(
        self, session: ImpersonationSession, staff_admin: Any
    ) -> None:
        end_impersonation(
            session_id=session.id,
            ended_by_user_id=staff_admin.id,
        )
        events = captured_audit_events(event_type="IMPERSONATION_ENDED")
        assert len(events) >= 1
        evt = events[-1]
        assert evt.actor_id == staff_admin.id
        assert evt.organization_id == session.organization_id
        assert evt.on_behalf_of_id == session.target_user_id
        assert evt.metadata is not None
        assert evt.metadata["end_reason"] == ImpersonationEndReason.ADMIN_ENDED
        assert evt.metadata["admin_user_id"] == str(session.admin_user_id)

    def test_duration_recorded_in_metadata(
        self, session: ImpersonationSession, staff_admin: Any
    ) -> None:
        end_impersonation(
            session_id=session.id,
            ended_by_user_id=staff_admin.id,
        )
        events = captured_audit_events(event_type="IMPERSONATION_ENDED")
        evt = events[-1]
        assert "duration_seconds" in evt.metadata  # type: ignore[operator]
        assert evt.metadata["duration_seconds"] >= 0  # type: ignore[index]

    def test_end_by_different_staff_succeeds(
        self,
        session: ImpersonationSession,
        user_factory: Any,
    ) -> None:
        """A different staff user can end someone else's session."""
        other_staff = user_factory(email="other-staff@example.test")
        other_staff.is_staff = True
        other_staff.save()

        result = end_impersonation(
            session_id=session.id,
            ended_by_user_id=other_staff.id,
        )
        assert result.ended_by_user_id == other_staff.id

    def test_end_with_logout_reason(
        self, session: ImpersonationSession, staff_admin: Any
    ) -> None:
        result = end_impersonation(
            session_id=session.id,
            ended_by_user_id=staff_admin.id,
            end_reason=ImpersonationEndReason.LOGOUT,
        )
        assert result.end_reason == ImpersonationEndReason.LOGOUT


@pytest.mark.django_db
class TestEndImpersonationErrors:
    def test_session_not_found_raises(self, staff_admin: Any) -> None:
        random_id = uuid4()
        with pytest.raises(ImpersonationSessionNotFoundError):
            end_impersonation(
                session_id=random_id,
                ended_by_user_id=staff_admin.id,
            )

    def test_already_ended_raises(
        self, session: ImpersonationSession, staff_admin: Any
    ) -> None:
        # End once.
        end_impersonation(
            session_id=session.id,
            ended_by_user_id=staff_admin.id,
        )
        # End again — should raise.
        with pytest.raises(ImpersonationSessionAlreadyEndedError):
            end_impersonation(
                session_id=session.id,
                ended_by_user_id=staff_admin.id,
            )

    def test_invalid_end_reason_raises(
        self, session: ImpersonationSession, staff_admin: Any
    ) -> None:
        with pytest.raises(ValueError):
            end_impersonation(
                session_id=session.id,
                ended_by_user_id=staff_admin.id,
                end_reason="not_a_valid_choice",
            )


@pytest.mark.django_db
class TestEndImpersonationFreesAdminSlot:
    def test_admin_can_start_new_session_after_ending(
        self,
        session: ImpersonationSession,
        staff_admin: Any,
        user_factory: Any,
    ) -> None:
        """After ending, the admin can start a new impersonation."""
        end_impersonation(
            session_id=session.id,
            ended_by_user_id=staff_admin.id,
        )
        # Now start a new session — must succeed.
        new_target = user_factory(email="new-target@example.test")
        new_org = Organization.objects.create(
            slug="new-org",
            name="New Org",
            primary_contact_email="new@example.test",
        )
        new_membership = Membership.objects.create(
            user=new_target,
            organization=new_org,
            status=MembershipStatus.ACTIVE,
        )
        new_session = start_impersonation(
            admin_user_id=staff_admin.id,
            target_user_id=new_target.id,
            organization_id=new_org.id,
            membership_id=new_membership.id,
            reason=_VALID_REASON,
        )
        assert new_session.id != session.id
        assert new_session.is_active is True
