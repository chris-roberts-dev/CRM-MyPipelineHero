"""Tests for TenantManager / TenantQuerySet surface (B.1.4).

These tests don't require any concrete tenant-owned model to exist. They
verify the manager class properties and the queryset's method
signatures.

We deliberately don't try to exercise ``for_org`` end-to-end with a
synthetic queryset: ``.filter(organization_id=...)`` requires a bound
model to resolve the field name, and constructing a fake model just to
test the signature is more cost than the test is worth. The real
``for_org`` behavior gets covered the moment any tenant-owned model
appears in a domain test (M1 D3 onward).
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock
from uuid import uuid4

from apps.common.tenancy.managers import TenantManager, TenantQuerySet


def test_tenant_manager_use_in_migrations_is_false() -> None:
    assert TenantManager.use_in_migrations is False


def test_tenant_queryset_intersect_default_is_identity() -> None:
    """Base intersect_with_operating_scope returns self unchanged."""
    qs = TenantQuerySet()
    membership = MagicMock()
    membership.organization_id = uuid4()
    out = qs.intersect_with_operating_scope(membership)
    assert out is qs


def test_tenant_queryset_exposes_for_org() -> None:
    """``for_org`` is callable on TenantQuerySet."""
    assert callable(getattr(TenantQuerySet, "for_org", None))


def test_for_org_accepts_a_single_positional_argument() -> None:
    """``for_org(organization_id)`` accepts exactly one positional arg."""
    sig = inspect.signature(TenantQuerySet.for_org)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    assert len(params) == 1
    assert params[0].name == "organization_id"


def test_tenant_queryset_exposes_for_membership() -> None:
    """``for_membership`` is callable on TenantQuerySet."""
    assert callable(getattr(TenantQuerySet, "for_membership", None))


def test_for_membership_accepts_a_single_positional_argument() -> None:
    """``for_membership(membership)`` accepts exactly one positional arg."""
    sig = inspect.signature(TenantQuerySet.for_membership)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    assert len(params) == 1
    assert params[0].name == "membership"


def test_tenant_manager_inherits_queryset_methods() -> None:
    """``TenantManager`` exposes ``for_org`` and ``for_membership`` as proxies.

    ``Manager.from_queryset(TenantQuerySet)`` generates manager methods
    that delegate to the queryset's methods of the same name. We don't
    invoke them here (that requires a bound model); we just confirm the
    attributes exist on the manager class.
    """
    assert callable(getattr(TenantManager, "for_org", None))
    assert callable(getattr(TenantManager, "for_membership", None))
