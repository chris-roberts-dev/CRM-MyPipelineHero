"""Tenancy helpers (B.1.6, B.2.6).

These utilities are called from service-layer code to enforce the
tenant-isolation and operating-scope invariants. They are NOT called
from views, models, or migrations.
"""

from __future__ import annotations

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
    # Avoid the circular import: Organization is in platform_organizations
    # which imports tenancy primitives indirectly. We duck-type by
    # checking attributes.
    if hasattr(record, "organization_id"):
        org_id = record.organization_id
        return org_id if org_id is not None else None
    # An Organization instance has no organization_id; it IS the org.
    # Detect via model label so this stays type-agnostic.
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
            ``Organization`` instance. ``None`` values are skipped
            (convenience for optional FKs).

    Returns:
        The common ``organization_id`` shared by all non-None records.

    Raises:
        TenantViolationError: if records belong to different orgs, or
            if any record lacks a resolvable org id.
        ValueError: if called with fewer than one non-None record.

    Examples:

        Allowed::

            ensure_same_org(quote, client, location)

        Raises ``TenantViolationError``::

            quote.organization_id == A; client.organization_id == B
            ensure_same_org(quote, client)
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


def resolve_location_ids_for_scopes(scopes: Any) -> list[UUID]:
    """Resolve a membership's scope assignments to a flat set of Location ids.

    A membership scope assignment can be at Region, Market, or Location
    granularity (B.2.4). This helper expands each assignment to the
    leaf Location set it covers:

        - REGION assignment → all Locations under all Markets under that Region
        - MARKET assignment → all Locations under that Market
        - LOCATION assignment → that Location only

    Args:
        scopes: an iterable of :class:`MembershipScopeAssignment` rows.

    Returns:
        A list of Location UUIDs covered by the scopes (deduplicated).

    Raises:
        NotImplementedError: always, in M1. The Region/Market/Location
            models land later in M1 (B.2.2); this helper gains a real
            implementation once those models exist. Calling this stub
            from M1 D1 code is a bug.
    """
    raise NotImplementedError(
        "resolve_location_ids_for_scopes is a stub. The Region/Market/Location "
        "models land later in M1 (B.2.2). Once they exist, this helper will "
        "walk the scope assignments and return the covered Location ids. "
        "If you hit this in code that runs today, you have a logic error."
    )
