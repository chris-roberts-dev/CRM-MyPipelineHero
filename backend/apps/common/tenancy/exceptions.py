"""Tenancy-related exceptions (B.1.6, B.2.6).

These exceptions signal violations of the tenant-isolation invariants.
They are not user-facing error messages — services that catch them
should treat them as 500-level bugs (the calling code should never
have constructed the cross-tenant query in the first place).

Services raise these by calling :func:`ensure_same_org` or by
invoking the RBAC object-check helpers (lands in M2).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID


class TenantViolationError(Exception):
    """Raised when a service-layer call mixes records from different orgs.

    Per B.1.6, when a tenant-owned record references another
    tenant-owned record, both MUST belong to the same Organization.
    This exception fires when :func:`ensure_same_org` detects a
    cross-tenant mix.

    Attributes:
        record_summaries: list of ``"<ModelName>(id=<id>, org=<org_id>)"``
            strings, one per record that participated in the violation.
            Useful for logs; never expose to end users.
    """

    def __init__(
        self,
        message: str,
        *,
        record_summaries: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.record_summaries: list[str] = list(record_summaries or [])


class OperatingScopeViolationError(Exception):
    """Raised when a membership's operating scope does not cover a target record.

    Per B.2.6, when a membership has scope assignments (Region/Market/
    Location) and the target record carries a ``location_id``, the
    location MUST fall within the membership's permitted location set.
    This exception fires when it does not.

    Attributes:
        membership_id: the membership whose scope was insufficient.
        target_location_id: the location the membership cannot reach.
    """

    def __init__(
        self,
        message: str = "Membership scope does not cover the target record.",
        *,
        membership: Any | None = None,
        target_location_id: UUID | None = None,
    ) -> None:
        super().__init__(message)
        # Stored as the raw membership object so callers can introspect
        # without forcing an import cycle. Read-only by convention.
        self.membership: Any | None = membership
        self.target_location_id: UUID | None = target_location_id
