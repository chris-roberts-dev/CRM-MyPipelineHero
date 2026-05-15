"""Tenancy helpers (B.1.6, B.2.6).

These utilities are called from service-layer code to enforce the
tenant-isolation and operating-scope invariants. They are NOT called
from views, models, or migrations.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any
from uuid import UUID

from apps.common.tenancy.exceptions import TenantViolationError

if TYPE_CHECKING:
    pass


def _record_org_id(record: Any) -> UUID | None:
    """Extract the org id from a record.

    Handles three shapes:
      - ``TenantOwnedModel`` subclasses: ``record.organization_id``
      - ``Organization`` instances: ``record.id`` (the org IS the tenant)
      - Anything else: returns None (caller decides whether to raise)
    """
    if hasattr(record, "organization_id"):
        org_id = record.organization_id
        return org_id if org_id is not None else None
    model_label = getattr(record._meta, "label", "") if hasattr(record, "_meta") else ""
    if model_label == "platform_organizations.Organization":
        return record.id
    return None


def _record_summary(record: Any) -> str:
    """Produce a short, log-safe summary of a record for error context."""
    model = type(record).__name__
    rid = getattr(record, "id", None) or getattr(record, "pk", None)
    org_id = _record_org_id(record)
    return f"{model}(id={rid}, org={org_id})"


def ensure_same_org(*records: Any) -> UUID:
    """Verify every record belongs to the same Organization (B.1.6 #1).

    Service-layer code passes the records it is about to write or
    join. If any pair of records carries a different ``organization_id``,
    this function raises :exc:`TenantViolationError`.

    Args:
        *records: Two or more records to check. Each MUST be either a
            ``TenantOwnedModel`` subclass instance or an
            ``Organization`` instance. ``None`` values are skipped.

    Returns:
        The common ``organization_id`` shared by all non-None records.

    Raises:
        TenantViolationError: if records belong to different orgs, or
            if any record lacks a resolvable org id.
        ValueError: if called with fewer than one non-None record.
    """
    non_null = [r for r in records if r is not None]
    if not non_null:
        raise ValueError("ensure_same_org requires at least one non-None record.")

    org_ids: list[UUID] = []
    summaries: list[str] = []
    for record in non_null:
        org_id = _record_org_id(record)
        if org_id is None:
            raise TenantViolationError(
                f"Record has no resolvable organization id: {_record_summary(record)}",
                record_summaries=[_record_summary(record)],
            )
        org_ids.append(org_id)
        summaries.append(_record_summary(record))

    first = org_ids[0]
    for other in org_ids[1:]:
        if other != first:
            raise TenantViolationError(
                "Cross-tenant record mix detected; all records must belong "
                "to the same Organization.",
                record_summaries=summaries,
            )
    return first


def resolve_location_ids_for_scopes(scopes: Iterable[Any]) -> list[UUID]:
    """Resolve a membership's scope assignments to a flat list of Location ids.

    A MembershipScopeAssignment can be at Region, Market, or Location
    granularity (B.2.4). This helper expands each assignment to the
    leaf Location set it covers:

        - REGION assignment   → all Locations under all Markets under that Region
        - MARKET assignment   → all Locations under that Market
        - LOCATION assignment → that Location only

    The result is deduplicated.

    Implementation strategy: bucket the input by scope_type, then issue
    one query per scope_type (REGION → Location.objects.filter(
    market__region_id__in=...), MARKET → Location.objects.filter(
    market_id__in=...), LOCATION → the literal IDs). This is at most
    three queries regardless of how many scope rows the membership has,
    so there is no N+1 over the scope list.

    Args:
        scopes: an iterable of MembershipScopeAssignment rows. May be
            an empty iterable, in which case the result is ``[]``.

    Returns:
        A list of Location UUIDs covered by the scopes, deduplicated.
        Order is unspecified.
    """
    region_ids: set[UUID] = set()
    market_ids: set[UUID] = set()
    location_ids: set[UUID] = set()

    for scope in scopes:
        if scope.region_id is not None:
            region_ids.add(scope.region_id)
        elif scope.market_id is not None:
            market_ids.add(scope.market_id)
        elif scope.location_id is not None:
            location_ids.add(scope.location_id)
        # The CHECK constraint guarantees at least one is non-null. We
        # don't raise here on an all-null row because we trust the DB
        # constraint to have caught it at write time.

    if not region_ids and not market_ids and not location_ids:
        return []

    # Local import to dodge the circular dependency: this module is
    # imported from apps.common.tenancy at startup, and Location lives
    # in apps.operations.locations which itself depends on tenancy.
    from apps.operations.locations.models import Location

    permitted: set[UUID] = set(location_ids)

    if market_ids:
        permitted.update(
            Location.objects.filter(market_id__in=market_ids).values_list(
                "id", flat=True
            )
        )

    if region_ids:
        permitted.update(
            Location.objects.filter(market__region_id__in=region_ids).values_list(
                "id", flat=True
            )
        )

    return list(permitted)
