"""Tests for ImpersonationSession model constraints (M1 D7 Phase 4)."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.platform.accounts.impersonation.models import (
    ImpersonationEndReason,
    ImpersonationSession,
)
from apps.platform.organizations.models import (
    Membership,
    MembershipStatus,
    Organization,
)


@pytest.fixture
def staff_admin(user_factory: Any) -> Any:
    user = user_factory(email="admin-model@example.test")
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def regular_target(user_factory: Any) -> Any:
    return user_factory(email="target-model@example.test")


@pytest.fixture
def org_and_membership(
    regular_target: Any,
) -> tuple[Organization, Membership]:
    org = Organization.objects.create(
        slug="imp-org",
        name="Impersonation Org",
        primary_contact_email="imp@example.test",
    )
    membership = Membership.objects.create(
        user=regular_target,
        organization=org,
        status=MembershipStatus.ACTIVE,
    )
    return org, membership


@pytest.mark.django_db
class TestImpersonationSessionCheckConstraints:
    def test_admin_cannot_equal_target(
        self,
        staff_admin: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        """DB CHECK: admin_user != target_user."""
        org, membership = org_and_membership
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ImpersonationSession.objects.create(
                    admin_user=staff_admin,
                    target_user=staff_admin,
                    organization=org,
                    membership=membership,
                    reason="self-impersonation should fail at DB",
                )

    def test_ended_at_before_started_rejected(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        """DB CHECK: ended_at >= started_at when set."""
        org, membership = org_and_membership
        # Create a session, then try to update ended_at to BEFORE
        # started_at. Need to query started_at then bump ended_at
        # past it.
        session = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="testing ended_at constraint",
        )
        # Try to set ended_at to before started_at directly via SQL.
        from datetime import timedelta

        bad_ended = session.started_at - timedelta(seconds=1)
        session.ended_at = bad_ended
        session.ended_by_user = staff_admin
        session.end_reason = ImpersonationEndReason.ADMIN_ENDED
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                session.save(
                    update_fields=[
                        "ended_at",
                        "ended_by_user",
                        "end_reason",
                    ]
                )

    def test_ended_pair_must_be_set_together_both_null(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        """DB CHECK: both ended_at + ended_by_user null, or both set.

        Test: setting only ended_at without ended_by_user fails.
        """
        org, membership = org_and_membership
        session = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="testing ended pair constraint",
        )
        session.ended_at = timezone.now()
        # Don't set ended_by_user — should violate the constraint.
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                session.save(update_fields=["ended_at"])

    def test_at_most_one_active_session_per_admin(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
        user_factory: Any,
    ) -> None:
        """Partial unique index: one active impersonation per admin."""
        org, membership = org_and_membership
        # First active session: succeeds.
        ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="first active session",
        )
        # Try to create a second active session for the same admin,
        # different target — DB rejects via the partial unique index.
        other_target = user_factory(email="other-target@example.test")
        other_membership = Membership.objects.create(
            user=other_target,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ImpersonationSession.objects.create(
                    admin_user=staff_admin,
                    target_user=other_target,
                    organization=org,
                    membership=other_membership,
                    reason="should fail: admin already has active session",
                )

    def test_admin_can_start_new_session_after_ending_first(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
        user_factory: Any,
    ) -> None:
        """End the first session, then a new one can start."""
        org, membership = org_and_membership
        first = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="first session to be ended",
        )
        # End it.
        first.ended_at = timezone.now()
        first.ended_by_user = staff_admin
        first.end_reason = ImpersonationEndReason.ADMIN_ENDED
        first.save(update_fields=["ended_at", "ended_by_user", "end_reason"])

        # Now a new session for the same admin can be created.
        other_target = user_factory(email="another-target@example.test")
        other_membership = Membership.objects.create(
            user=other_target,
            organization=org,
            status=MembershipStatus.ACTIVE,
        )
        new_session = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=other_target,
            organization=org,
            membership=other_membership,
            reason="second session after ending first",
        )
        assert new_session.id != first.id


@pytest.mark.django_db
class TestImpersonationSessionManager:
    def test_active_for_admin_returns_active_session(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        session = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="active session for active_for_admin",
        )
        found = ImpersonationSession.objects.active_for_admin(staff_admin.id)
        assert found is not None
        assert found.id == session.id

    def test_active_for_admin_returns_none_when_none_active(
        self, staff_admin: Any
    ) -> None:
        found = ImpersonationSession.objects.active_for_admin(staff_admin.id)
        assert found is None

    def test_active_for_admin_returns_none_for_ended_session(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        session = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="ended session, not active",
        )
        # End it.
        session.ended_at = timezone.now()
        session.ended_by_user = staff_admin
        session.end_reason = ImpersonationEndReason.ADMIN_ENDED
        session.save(update_fields=["ended_at", "ended_by_user", "end_reason"])

        found = ImpersonationSession.objects.active_for_admin(staff_admin.id)
        assert found is None


@pytest.mark.django_db
class TestImpersonationSessionProperties:
    def test_is_active_true_for_open_session(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        session = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="active session property test",
        )
        assert session.is_active is True

    def test_is_active_false_for_ended_session(
        self,
        staff_admin: Any,
        regular_target: Any,
        org_and_membership: tuple[Organization, Membership],
    ) -> None:
        org, membership = org_and_membership
        session = ImpersonationSession.objects.create(
            admin_user=staff_admin,
            target_user=regular_target,
            organization=org,
            membership=membership,
            reason="ended session property test",
        )
        session.ended_at = timezone.now()
        session.ended_by_user = staff_admin
        session.end_reason = ImpersonationEndReason.ADMIN_ENDED
        session.save(update_fields=["ended_at", "ended_by_user", "end_reason"])
        session.refresh_from_db()
        assert session.is_active is False
