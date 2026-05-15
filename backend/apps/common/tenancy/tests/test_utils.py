"""Tests for apps.common.tenancy.utils."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from apps.common.tenancy.exceptions import TenantViolationError
from apps.common.tenancy.utils import (
    ensure_same_org,
    resolve_location_ids_for_scopes,
)

# ---------------------------------------------------------------------------
# ensure_same_org
# ---------------------------------------------------------------------------


def _fake_record(*, organization_id):
    rec = MagicMock()
    rec.organization_id = organization_id
    rec.id = uuid4()
    rec.pk = rec.id
    rec.configure_mock(__class__=type("FakeRecord", (), {}))
    return rec


def test_ensure_same_org_passes_for_matching_records() -> None:
    org = uuid4()
    a = _fake_record(organization_id=org)
    b = _fake_record(organization_id=org)
    c = _fake_record(organization_id=org)
    assert ensure_same_org(a, b, c) == org


def test_ensure_same_org_raises_on_mismatch() -> None:
    a = _fake_record(organization_id=uuid4())
    b = _fake_record(organization_id=uuid4())
    with pytest.raises(TenantViolationError) as excinfo:
        ensure_same_org(a, b)
    assert "Cross-tenant" in str(excinfo.value)
    assert len(excinfo.value.record_summaries) == 2


def test_ensure_same_org_skips_none_records() -> None:
    org = uuid4()
    a = _fake_record(organization_id=org)
    b = _fake_record(organization_id=org)
    assert ensure_same_org(a, None, b, None) == org


def test_ensure_same_org_raises_when_all_records_are_none() -> None:
    with pytest.raises(ValueError):
        ensure_same_org(None, None)


def test_ensure_same_org_raises_when_record_has_no_org() -> None:
    rogue = MagicMock(spec=[])
    with pytest.raises(TenantViolationError) as excinfo:
        ensure_same_org(rogue)
    assert "no resolvable organization id" in str(excinfo.value)


@pytest.mark.django_db
def test_ensure_same_org_accepts_organization_instance() -> None:
    """An Organization passed in returns its own id as the common org id."""
    from apps.platform.organizations.models import Organization

    org = Organization.objects.create(
        slug="tenancy-test",
        name="Tenancy Test",
        primary_contact_email="ops@example.test",
    )
    a = _fake_record(organization_id=org.id)
    assert ensure_same_org(org, a) == org.id


# ---------------------------------------------------------------------------
# resolve_location_ids_for_scopes — basic shape
# ---------------------------------------------------------------------------


def test_resolve_with_empty_iterable_returns_empty_list() -> None:
    """The function accepts an empty iterable without touching the DB."""
    assert resolve_location_ids_for_scopes([]) == []


def test_resolve_with_iterator_input_also_works() -> None:
    """Passing a generator instead of a list works."""
    result = resolve_location_ids_for_scopes(iter([]))
    assert result == []


# The full happy-path tests for REGION / MARKET / LOCATION granularity
# live alongside the RML models at
# apps/operations/locations/tests/test_models.py — they require Region,
# Market, Location, MembershipScopeAssignment which all live in another
# app, and putting them there keeps the import graph clean.
