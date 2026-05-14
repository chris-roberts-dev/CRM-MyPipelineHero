"""Organization service layer (M1 D2).

Public API:

* :func:`create_organization` — provision a new tenant with cloned
  per-tenant role rows.
* :func:`assign_owner_membership` — bootstrap the first ACTIVE
  Membership for a tenant and assign the per-tenant Owner role.

Service-layer rules (A.4.4):

* Functions accept primitive arguments (UUIDs, strings, decimals).
  They do not accept request objects.
* Functions own their transaction boundaries via
  ``transaction.atomic(...)``.
* Audit events are emitted via :func:`apps.platform.audit.services.audit_emit`
  inside the same atomic boundary as the state change they describe.

Exceptions (defined in :mod:`apps.platform.organizations.services.exceptions`):

* :exc:`OrganizationSlugInUseError` — slug collision on create.
* :exc:`OrganizationNotFoundError` — caller referenced a nonexistent org.
* :exc:`UserNotFoundError` — caller referenced a nonexistent user.
* :exc:`MembershipAlreadyExistsError` — user already has a Membership
  in the target organization.
"""

from __future__ import annotations

from apps.platform.organizations.services._create import (
    assign_owner_membership,
    create_organization,
)
from apps.platform.organizations.services.exceptions import (
    MembershipAlreadyExistsError,
    OrganizationNotFoundError,
    OrganizationSlugInUseError,
    UserNotFoundError,
)

__all__ = [
    "MembershipAlreadyExistsError",
    "OrganizationNotFoundError",
    "OrganizationSlugInUseError",
    "UserNotFoundError",
    "assign_owner_membership",
    "create_organization",
]
