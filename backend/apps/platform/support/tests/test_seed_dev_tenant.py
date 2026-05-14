"""Tests for the seed_dev_tenant management command (M0 D4).

These tests verify J.2.4 exit criterion #1 — that a dev tenant can be
seeded reproducibly and idempotently.
"""

from __future__ import annotations

import io

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.management import call_command

SLUG = "demo"
ADMIN_EMAIL = "admin@mph.local"
ADMIN_PASSWORD = "mph-demo-password!"


@pytest.fixture
def Organization():
    return django_apps.get_model("platform_organizations", "Organization")


@pytest.fixture
def Membership():
    return django_apps.get_model("platform_organizations", "Membership")


@pytest.fixture
def Role():
    return django_apps.get_model("platform_rbac", "Role")


@pytest.fixture
def RoleCapability():
    return django_apps.get_model("platform_rbac", "RoleCapability")


@pytest.fixture
def MembershipRole():
    return django_apps.get_model("platform_rbac", "MembershipRole")


def _call() -> str:
    """Run the command and capture stdout for assertion."""
    out = io.StringIO()
    call_command(
        "seed_dev_tenant",
        "--slug",
        SLUG,
        "--admin-email",
        ADMIN_EMAIL,
        "--admin-password",
        ADMIN_PASSWORD,
        stdout=out,
    )
    return out.getvalue()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_first_run_creates_full_tenant_state(
    Organization, Membership, Role, RoleCapability, MembershipRole
) -> None:
    output = _call()

    # Organization created
    assert Organization.objects.filter(slug=SLUG).count() == 1
    org = Organization.objects.get(slug=SLUG)
    assert org.status == "ACTIVE"

    # Admin user created
    User = get_user_model()
    assert User.objects.filter(email=ADMIN_EMAIL).count() == 1
    user = User.objects.get(email=ADMIN_EMAIL)
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.has_usable_password() is True
    assert user.check_password(ADMIN_PASSWORD) is True

    # 11 per-tenant roles created
    tenant_roles = Role.objects.filter(organization=org)
    assert tenant_roles.count() == 11

    # Per-tenant Owner role exists, is not locked, is not a template
    owner = tenant_roles.get(code="owner")
    assert owner.is_default is False
    assert owner.is_locked is False
    assert owner.is_scoped_role is False

    # Per-tenant Owner role has the same capabilities as the template
    template_owner = Role.objects.get(organization__isnull=True, code="owner")
    template_codes = set(
        RoleCapability.objects.filter(role=template_owner).values_list(
            "capability__code", flat=True
        )
    )
    tenant_codes = set(
        RoleCapability.objects.filter(role=owner).values_list(
            "capability__code", flat=True
        )
    )
    assert template_codes == tenant_codes
    assert len(template_codes) > 0  # sanity: not an empty match

    # Membership exists and is the user's default membership
    membership = Membership.objects.get(user=user, organization=org)
    assert membership.status == "ACTIVE"
    assert membership.is_default_for_user is True

    # Owner role assigned to membership
    assert MembershipRole.objects.filter(membership=membership, role=owner).count() == 1

    # Output mentions URL + credentials
    assert "http://mph.local/login/" in output
    assert ADMIN_EMAIL in output


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_second_run_is_idempotent(
    Organization, Membership, Role, RoleCapability, MembershipRole
) -> None:
    _call()

    User = get_user_model()
    org_count_before = Organization.objects.count()
    user_count_before = User.objects.count()
    tenant_role_count_before = Role.objects.filter(organization__slug=SLUG).count()
    membership_count_before = Membership.objects.count()
    assignment_count_before = MembershipRole.objects.count()

    _call()

    assert Organization.objects.count() == org_count_before
    assert User.objects.count() == user_count_before
    assert (
        Role.objects.filter(organization__slug=SLUG).count() == tenant_role_count_before
    )
    assert Membership.objects.count() == membership_count_before
    assert MembershipRole.objects.count() == assignment_count_before


# ---------------------------------------------------------------------------
# --reset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reset_recreates_clean_tenant(Organization, Membership, Role) -> None:
    _call()
    org = Organization.objects.get(slug=SLUG)
    original_id = org.id

    # Run with --reset
    out = io.StringIO()
    call_command(
        "seed_dev_tenant",
        "--slug",
        SLUG,
        "--admin-email",
        ADMIN_EMAIL,
        "--admin-password",
        ADMIN_PASSWORD,
        "--reset",
        stdout=out,
    )

    # New Organization row with the same slug, different id
    org_after = Organization.objects.get(slug=SLUG)
    assert org_after.id != original_id

    # Still has 11 per-tenant roles
    assert Role.objects.filter(organization=org_after).count() == 11

    # Still has a single Membership for the admin
    User = get_user_model()
    user = User.objects.get(email=ADMIN_EMAIL)
    assert Membership.objects.filter(user=user, organization=org_after).count() == 1


# ---------------------------------------------------------------------------
# Pre-flight guards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_command_fails_if_seed_v1_has_not_run(Role) -> None:
    """If templates are missing, the command refuses to run."""
    # Wipe template roles
    Role.objects.filter(organization__isnull=True, is_default=True).delete()

    out = io.StringIO()
    err = io.StringIO()
    with pytest.raises(Exception) as excinfo:
        call_command(
            "seed_dev_tenant",
            "--slug",
            SLUG,
            "--admin-email",
            ADMIN_EMAIL,
            stdout=out,
            stderr=err,
        )
    assert "seed_v1" in str(excinfo.value) or "default role templates" in str(
        excinfo.value
    )


# ---------------------------------------------------------------------------
# System user invariant
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_does_not_touch_system_user() -> None:
    User = get_user_model()
    system_user_count_before = User.objects.filter(is_system=True).count()

    _call()
    call_command(
        "seed_dev_tenant",
        "--slug",
        SLUG,
        "--admin-email",
        ADMIN_EMAIL,
        "--admin-password",
        ADMIN_PASSWORD,
        "--reset",
        stdout=io.StringIO(),
    )

    system_user_count_after = User.objects.filter(is_system=True).count()
    assert system_user_count_after == system_user_count_before == 1
