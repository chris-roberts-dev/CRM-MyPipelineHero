"""Tests for RML models (B.2.2) and the operating-scope intersection (B.2.5)."""

from __future__ import annotations

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.common.tenancy.utils import resolve_location_ids_for_scopes
from apps.operations.locations.models import Location, Market, Region
from apps.platform.organizations.services import (
    assign_owner_membership,
    create_organization,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def Organization():
    return django_apps.get_model("platform_organizations", "Organization")


@pytest.fixture
def Membership():
    return django_apps.get_model("platform_organizations", "Membership")


@pytest.fixture
def MembershipScopeAssignment():
    return django_apps.get_model("platform_organizations", "MembershipScopeAssignment")


@pytest.fixture
def system_user_id():
    User = get_user_model()
    return User.objects.get(is_system=True).id


@pytest.fixture
def org_a(system_user_id):
    return create_organization(
        slug="rml-a",
        name="RML Org A",
        primary_contact_email="ops@rml-a.example",
        actor_id=system_user_id,
    )


@pytest.fixture
def org_b(system_user_id):
    return create_organization(
        slug="rml-b",
        name="RML Org B",
        primary_contact_email="ops@rml-b.example",
        actor_id=system_user_id,
    )


@pytest.fixture
def rml_tree(org_a):
    """Build a small RML tree on org_a:

    Region NORTH
      Market NORTH-A
        Location N-A-1
        Location N-A-2
      Market NORTH-B
        Location N-B-1
    Region SOUTH
      Market SOUTH-A
        Location S-A-1
    """
    north = Region.objects.create(organization=org_a, code="NORTH", name="North")
    south = Region.objects.create(organization=org_a, code="SOUTH", name="South")

    north_a = Market.objects.create(
        organization=org_a, region=north, code="NORTH-A", name="North A"
    )
    north_b = Market.objects.create(
        organization=org_a, region=north, code="NORTH-B", name="North B"
    )
    south_a = Market.objects.create(
        organization=org_a, region=south, code="SOUTH-A", name="South A"
    )

    n_a_1 = Location.objects.create(
        organization=org_a, market=north_a, code="N-A-1", name="North A One"
    )
    n_a_2 = Location.objects.create(
        organization=org_a, market=north_a, code="N-A-2", name="North A Two"
    )
    n_b_1 = Location.objects.create(
        organization=org_a, market=north_b, code="N-B-1", name="North B One"
    )
    s_a_1 = Location.objects.create(
        organization=org_a, market=south_a, code="S-A-1", name="South A One"
    )

    return {
        "regions": {"north": north, "south": south},
        "markets": {"north_a": north_a, "north_b": north_b, "south_a": south_a},
        "locations": {
            "n_a_1": n_a_1,
            "n_a_2": n_a_2,
            "n_b_1": n_b_1,
            "s_a_1": s_a_1,
        },
    }


# ---------------------------------------------------------------------------
# Creation flows
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_region(org_a) -> None:
    region = Region.objects.create(organization=org_a, code="WEST", name="West")
    assert region.id is not None
    assert region.is_active is True
    assert region.organization_id == org_a.id


@pytest.mark.django_db
def test_create_market_under_region(org_a) -> None:
    region = Region.objects.create(organization=org_a, code="EAST", name="East")
    market = Market.objects.create(
        organization=org_a, region=region, code="EAST-PRIMARY", name="East Primary"
    )
    assert market.region_id == region.id
    assert market.organization_id == org_a.id


@pytest.mark.django_db
def test_create_location_under_market(org_a) -> None:
    region = Region.objects.create(organization=org_a, code="MID", name="Mid")
    market = Market.objects.create(
        organization=org_a, region=region, code="MID-1", name="Mid 1"
    )
    location = Location.objects.create(
        organization=org_a,
        market=market,
        code="MID-1-SITE",
        name="Mid 1 Site",
        address_line1="100 Main St",
        city="Anywhere",
        region_admin="TN",
        postal_code="38501",
        country="US",
    )
    assert location.market_id == market.id
    assert location.organization_id == org_a.id
    assert location.tax_jurisdiction_id is None  # plain UUID; nothing assigned


# ---------------------------------------------------------------------------
# unique_together
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_region_unique_together_organization_code(org_a) -> None:
    Region.objects.create(organization=org_a, code="DUP", name="Dup A")
    with pytest.raises(IntegrityError), transaction.atomic():
        Region.objects.create(organization=org_a, code="DUP", name="Dup B")


@pytest.mark.django_db
def test_region_code_can_repeat_across_orgs(org_a, org_b) -> None:
    """Same code is fine across different orgs."""
    Region.objects.create(organization=org_a, code="SHARED", name="Shared A")
    # Should NOT raise.
    Region.objects.create(organization=org_b, code="SHARED", name="Shared B")


@pytest.mark.django_db
def test_market_unique_together_organization_code(org_a) -> None:
    r = Region.objects.create(organization=org_a, code="R", name="R")
    Market.objects.create(organization=org_a, region=r, code="DUP", name="Dup A")
    with pytest.raises(IntegrityError), transaction.atomic():
        Market.objects.create(organization=org_a, region=r, code="DUP", name="Dup B")


@pytest.mark.django_db
def test_location_unique_together_organization_code(org_a) -> None:
    r = Region.objects.create(organization=org_a, code="R", name="R")
    m = Market.objects.create(organization=org_a, region=r, code="M", name="M")
    Location.objects.create(organization=org_a, market=m, code="DUP", name="Dup A")
    with pytest.raises(IntegrityError), transaction.atomic():
        Location.objects.create(organization=org_a, market=m, code="DUP", name="Dup B")


# ---------------------------------------------------------------------------
# Cross-organization chain prohibition (B.2.1 / B.1.6)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_cross_org_market_to_region_chain_caught_by_ensure_same_org(
    org_a, org_b
) -> None:
    """B.1.6 invariant: cross-org references are prohibited.

    There is no cross-row DB CHECK enforcing this (the guide rules
    those out for v1). Instead, service-layer code calls
    ``ensure_same_org`` before constructing the chain. This test
    verifies that helper catches the violation when it would happen.

    Note: at the ORM level, creating a Market in org_b with a Region
    from org_a would technically succeed. The protection is at the
    service-layer doorway. When the Market-creation service lands
    (M2+), it will call ``ensure_same_org(organization=org_b,
    region=region_a)`` and the helper will raise. We exercise that
    contract here.
    """
    from apps.common.tenancy.exceptions import TenantViolationError
    from apps.common.tenancy.utils import ensure_same_org

    region_a = Region.objects.create(organization=org_a, code="A-R", name="A R")

    with pytest.raises(TenantViolationError):
        # This is the check the future Market-creation service would
        # perform before calling Market.objects.create(...).
        ensure_same_org(org_b, region_a)


@pytest.mark.django_db
def test_cross_org_location_to_market_chain_caught_by_ensure_same_org(
    org_a, org_b
) -> None:
    """Same protection one level deeper in the chain."""
    from apps.common.tenancy.exceptions import TenantViolationError
    from apps.common.tenancy.utils import ensure_same_org

    region_a = Region.objects.create(organization=org_a, code="A-R", name="A R")
    market_a = Market.objects.create(
        organization=org_a, region=region_a, code="A-M", name="A M"
    )

    with pytest.raises(TenantViolationError):
        ensure_same_org(org_b, market_a)


# ---------------------------------------------------------------------------
# resolve_location_ids_for_scopes — REGION granularity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_region_scope_returns_all_locations_under_region(
    rml_tree, MembershipScopeAssignment, Membership, system_user_id, org_a
) -> None:
    # Build a membership for the system user on org_a
    user_id = system_user_id
    # The system user already has no membership on org_a — assign one.
    membership = assign_owner_membership(
        organization_id=org_a.id, user_id=user_id, actor_id=user_id
    )

    # Build a REGION scope assignment pointing at NORTH
    north = rml_tree["regions"]["north"]
    assignment = MembershipScopeAssignment.objects.create(
        membership=membership,
        scope_type="REGION",
        region=north,
    )

    permitted = resolve_location_ids_for_scopes([assignment])
    expected = {
        rml_tree["locations"]["n_a_1"].id,
        rml_tree["locations"]["n_a_2"].id,
        rml_tree["locations"]["n_b_1"].id,
    }
    assert set(permitted) == expected
    assert rml_tree["locations"]["s_a_1"].id not in permitted


# ---------------------------------------------------------------------------
# resolve_location_ids_for_scopes — MARKET granularity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_market_scope_returns_locations_under_market(
    rml_tree, MembershipScopeAssignment, system_user_id, org_a
) -> None:
    membership = assign_owner_membership(
        organization_id=org_a.id, user_id=system_user_id, actor_id=system_user_id
    )
    north_a = rml_tree["markets"]["north_a"]
    assignment = MembershipScopeAssignment.objects.create(
        membership=membership, scope_type="MARKET", market=north_a
    )

    permitted = resolve_location_ids_for_scopes([assignment])
    expected = {
        rml_tree["locations"]["n_a_1"].id,
        rml_tree["locations"]["n_a_2"].id,
    }
    assert set(permitted) == expected


# ---------------------------------------------------------------------------
# resolve_location_ids_for_scopes — LOCATION granularity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_location_scope_returns_only_that_location(
    rml_tree, MembershipScopeAssignment, system_user_id, org_a
) -> None:
    membership = assign_owner_membership(
        organization_id=org_a.id, user_id=system_user_id, actor_id=system_user_id
    )
    n_a_1 = rml_tree["locations"]["n_a_1"]
    assignment = MembershipScopeAssignment.objects.create(
        membership=membership, scope_type="LOCATION", location=n_a_1
    )

    permitted = resolve_location_ids_for_scopes([assignment])
    assert set(permitted) == {n_a_1.id}


# ---------------------------------------------------------------------------
# resolve_location_ids_for_scopes — mixed granularities
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_mixed_scopes_returns_union_dedupe(
    rml_tree, MembershipScopeAssignment, system_user_id, org_a
) -> None:
    """REGION + MARKET + LOCATION at once: union, deduplicated.

    Setup:
      REGION SOUTH (covers s_a_1)
      MARKET NORTH-A (covers n_a_1, n_a_2)
      LOCATION n_a_1 (already covered by NORTH-A; should dedupe)

    Expected: {n_a_1, n_a_2, s_a_1}
    """
    membership = assign_owner_membership(
        organization_id=org_a.id, user_id=system_user_id, actor_id=system_user_id
    )
    south = rml_tree["regions"]["south"]
    north_a = rml_tree["markets"]["north_a"]
    n_a_1 = rml_tree["locations"]["n_a_1"]

    a1 = MembershipScopeAssignment.objects.create(
        membership=membership, scope_type="REGION", region=south
    )
    a2 = MembershipScopeAssignment.objects.create(
        membership=membership, scope_type="MARKET", market=north_a
    )
    a3 = MembershipScopeAssignment.objects.create(
        membership=membership, scope_type="LOCATION", location=n_a_1
    )

    permitted = resolve_location_ids_for_scopes([a1, a2, a3])
    expected = {
        n_a_1.id,
        rml_tree["locations"]["n_a_2"].id,
        rml_tree["locations"]["s_a_1"].id,
    }
    assert set(permitted) == expected
    # No duplicates even though n_a_1 was covered twice
    assert len(permitted) == len(set(permitted))


@pytest.mark.django_db
def test_resolve_empty_scope_list_returns_empty_list() -> None:
    assert resolve_location_ids_for_scopes([]) == []


# ---------------------------------------------------------------------------
# LocationQuerySet.intersect_with_operating_scope (B.2.5 pattern)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_location_queryset_intersect_with_scoped_membership(
    rml_tree, MembershipScopeAssignment, system_user_id, org_a
) -> None:
    membership = assign_owner_membership(
        organization_id=org_a.id, user_id=system_user_id, actor_id=system_user_id
    )
    # Scope to NORTH-A market only
    MembershipScopeAssignment.objects.create(
        membership=membership,
        scope_type="MARKET",
        market=rml_tree["markets"]["north_a"],
    )

    qs = Location.objects.for_org(org_a.id).intersect_with_operating_scope(membership)
    visible_ids = set(qs.values_list("id", flat=True))
    expected = {
        rml_tree["locations"]["n_a_1"].id,
        rml_tree["locations"]["n_a_2"].id,
    }
    assert visible_ids == expected


@pytest.mark.django_db
def test_location_queryset_intersect_with_no_scopes_and_no_scoped_role(
    rml_tree, system_user_id, org_a
) -> None:
    """No scope assignments + Owner (non-scoped) role = org-wide access."""
    membership = assign_owner_membership(
        organization_id=org_a.id, user_id=system_user_id, actor_id=system_user_id
    )
    qs = Location.objects.for_org(org_a.id).intersect_with_operating_scope(membership)
    visible_ids = set(qs.values_list("id", flat=True))
    assert visible_ids == set(
        rml_tree["locations"][k].id for k in rml_tree["locations"]
    )


# ---------------------------------------------------------------------------
# MembershipScopeAssignment CHECK constraint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scope_assignment_check_requires_exactly_one_target(
    rml_tree, MembershipScopeAssignment, system_user_id, org_a
) -> None:
    membership = assign_owner_membership(
        organization_id=org_a.id, user_id=system_user_id, actor_id=system_user_id
    )
    north = rml_tree["regions"]["north"]
    north_a = rml_tree["markets"]["north_a"]

    # Two targets simultaneously → CHECK constraint violation
    with pytest.raises(IntegrityError), transaction.atomic():
        MembershipScopeAssignment.objects.create(
            membership=membership,
            scope_type="REGION",
            region=north,
            market=north_a,  # invalid: only one of region/market/location may be set
        )

    # Zero targets → CHECK constraint violation
    with pytest.raises(IntegrityError), transaction.atomic():
        MembershipScopeAssignment.objects.create(
            membership=membership,
            scope_type="REGION",
            # region/market/location all None
        )
