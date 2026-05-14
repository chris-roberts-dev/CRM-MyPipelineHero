"""Tests for apps.platform.organizations.services.assign_owner_membership."""

from __future__ import annotations

import uuid

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model

from apps.platform.audit.services import captured_audit_events
from apps.platform.organizations.services import (
    MembershipAlreadyExistsError,
    OrganizationNotFoundError,
    UserNotFoundError,
    assign_owner_membership,
    create_organization,
)


@pytest.fixture
def Organization():
    return django_apps.get_model("platform_organizations", "Organization")


@pytest.fixture
def Membership():
    return django_apps.get_model("platform_organizations", "Membership")


@pytest.fixture
def MembershipRole():
    return django_apps.get_model("platform_rbac", "MembershipRole")


@pytest.fixture
def system_user_id():
    User = get_user_model()
    return User.objects.get(is_system=True).id


@pytest.fixture
def fresh_user():
    User = get_user_model()
    user = User(email="newowner@example.example", is_active=True)
    user.set_password("strong-password-12345!")
    user.save()
    return user


@pytest.fixture
def fresh_org(system_user_id, Organization):
    return create_organization(
        slug="member-test",
        name="Member Test",
        primary_contact_email="ops@member-test.example",
        actor_id=system_user_id,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_happy_path_creates_membership_with_owner_role(
    fresh_org, fresh_user, system_user_id, Membership, MembershipRole
) -> None:
    membership = assign_owner_membership(
        organization_id=fresh_org.id,
        user_id=fresh_user.id,
        actor_id=system_user_id,
        first_name="New",
        last_name="Owner",
    )

    # Membership shape
    assert membership.user_id == fresh_user.id
    assert membership.organization_id == fresh_org.id
    assert membership.status == "ACTIVE"
    assert membership.is_default_for_user is True
    assert membership.first_name == "New"
    assert membership.last_name == "Owner"

    # MembershipRole linking to the per-tenant Owner role
    assignments = MembershipRole.objects.filter(membership=membership)
    assert assignments.count() == 1
    assignment = assignments.get()
    assert assignment.role.code == "owner"
    assert assignment.role.organization_id == fresh_org.id
    assert assignment.assigned_by_id == system_user_id


# ---------------------------------------------------------------------------
# Audit emission
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_assign_owner_emits_both_audit_events(
    fresh_org, fresh_user, system_user_id
) -> None:
    membership = assign_owner_membership(
        organization_id=fresh_org.id,
        user_id=fresh_user.id,
        actor_id=system_user_id,
    )

    created = captured_audit_events(
        event_type="MEMBERSHIP_CREATED", organization_id=fresh_org.id
    )
    assert len(created) == 1
    assert created[0].object_id == str(membership.id)
    assert created[0].actor_id == system_user_id

    assigned = captured_audit_events(
        event_type="ROLE_ASSIGNED", organization_id=fresh_org.id
    )
    assert len(assigned) == 1
    assert assigned[0].payload_after is not None
    assert assigned[0].payload_after["role_code"] == "owner"
    assert assigned[0].payload_after["membership_id"] == str(membership.id)


# ---------------------------------------------------------------------------
# Default-membership semantics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_second_org_for_same_user_is_not_default(
    fresh_user, system_user_id, Organization
) -> None:
    # First org → first membership is default.
    org_a = create_organization(
        slug="multi-a",
        name="Multi A",
        primary_contact_email="a@multi.example",
        actor_id=system_user_id,
    )
    m_a = assign_owner_membership(
        organization_id=org_a.id, user_id=fresh_user.id, actor_id=system_user_id
    )
    assert m_a.is_default_for_user is True

    # Second org → second membership is NOT default (user already has one).
    org_b = create_organization(
        slug="multi-b",
        name="Multi B",
        primary_contact_email="b@multi.example",
        actor_id=system_user_id,
    )
    m_b = assign_owner_membership(
        organization_id=org_b.id, user_id=fresh_user.id, actor_id=system_user_id
    )
    assert m_b.is_default_for_user is False


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_organization_raises_typed_exception(
    fresh_user, system_user_id
) -> None:
    with pytest.raises(OrganizationNotFoundError):
        assign_owner_membership(
            organization_id=uuid.uuid4(),
            user_id=fresh_user.id,
            actor_id=system_user_id,
        )


@pytest.mark.django_db
def test_missing_user_raises_typed_exception(fresh_org, system_user_id) -> None:
    with pytest.raises(UserNotFoundError):
        assign_owner_membership(
            organization_id=fresh_org.id,
            user_id=uuid.uuid4(),
            actor_id=system_user_id,
        )


@pytest.mark.django_db
def test_missing_actor_raises_typed_exception(fresh_org, fresh_user) -> None:
    with pytest.raises(UserNotFoundError):
        assign_owner_membership(
            organization_id=fresh_org.id,
            user_id=fresh_user.id,
            actor_id=uuid.uuid4(),
        )


@pytest.mark.django_db
def test_duplicate_membership_raises_typed_exception(
    fresh_org, fresh_user, system_user_id
) -> None:
    assign_owner_membership(
        organization_id=fresh_org.id,
        user_id=fresh_user.id,
        actor_id=system_user_id,
    )
    with pytest.raises(MembershipAlreadyExistsError):
        assign_owner_membership(
            organization_id=fresh_org.id,
            user_id=fresh_user.id,
            actor_id=system_user_id,
        )


# ---------------------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_role_assignment_failure_rolls_back_membership(
    fresh_org, fresh_user, system_user_id, Membership, monkeypatch
) -> None:
    """If the MembershipRole insert blows up, the Membership rolls back."""
    from apps.platform.rbac import models as rbac_models

    original_create = rbac_models.MembershipRole.objects.create

    def boom(*args, **kwargs):
        raise RuntimeError("simulated MembershipRole failure")

    monkeypatch.setattr(rbac_models.MembershipRole.objects, "create", boom)

    with pytest.raises(RuntimeError, match="simulated MembershipRole failure"):
        assign_owner_membership(
            organization_id=fresh_org.id,
            user_id=fresh_user.id,
            actor_id=system_user_id,
        )

    # The Membership was never committed.
    assert (
        Membership.objects.filter(user=fresh_user, organization=fresh_org).count() == 0
    )

    # Restore (monkeypatch undoes this automatically at test exit, but
    # belt-and-suspenders so a later assertion in this fixture chain
    # doesn't accidentally use the patched method).
    rbac_models.MembershipRole.objects.create = original_create
