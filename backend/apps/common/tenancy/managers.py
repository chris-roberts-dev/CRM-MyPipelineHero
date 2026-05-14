"""TenantManager and TenantQuerySet (B.1.4).

Tenant-aware ORM surface for :class:`TenantOwnedModel` subclasses.

``TenantManager`` does NOT auto-filter querysets. This is deliberate:

* B.1.5 permits two cross-tenant exception paths (Support User
  platform console + migrations). Auto-filtering would force every
  exception-path call to think about how to escape the filter, which
  inverts the safety posture.
* Service-layer code is the authoritative call site for tenant-scoped
  reads, and it uses the explicit ``for_org(...)`` / ``for_membership(...)``
  methods. The explicitness is a feature.

Models that need operating-scope intersection (B.2.5) — e.g.
SalesOrder, which carries ``location_id`` — override
``intersect_with_operating_scope`` on a per-model QuerySet subclass.
The base method returns ``self`` unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from django.db import models

if TYPE_CHECKING:
    from apps.platform.organizations.models import Membership


class TenantQuerySet(models.QuerySet):
    """Tenant-aware queryset surface (B.1.4)."""

    def for_org(self, organization_id: UUID) -> TenantQuerySet:
        """Filter to records belonging to a specific Organization.

        Args:
            organization_id: UUID of the target Organization.

        Returns:
            New queryset filtered on ``organization_id``.
        """
        return self.filter(organization_id=organization_id)

    def for_membership(self, membership: Membership) -> TenantQuerySet:
        """Apply org scope AND operating-scope intersection.

        Equivalent to::

            qs.for_org(membership.organization_id) \\
              .intersect_with_operating_scope(membership)

        Use this in service layer reads where the acting member's
        operating scope (Region/Market/Location) should restrict
        visibility (B.2.5).
        """
        qs = self.for_org(membership.organization_id)
        return qs.intersect_with_operating_scope(membership)

    def intersect_with_operating_scope(self, membership: Membership) -> TenantQuerySet:
        """Restrict to records covered by the membership's operating scope.

        The base implementation is a no-op (returns ``self``). Per-model
        QuerySet subclasses override this for models that carry a
        ``location_id`` field — see B.2.5 for the SalesOrder example.

        For models without a ``location_id`` field, the no-op base is
        the correct behavior: there is nothing to intersect against.
        """
        return self


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):  # type: ignore[misc]
    """Manager for :class:`TenantOwnedModel` subclasses.

    Two important properties:

    * ``use_in_migrations = False``: the Django migration framework
      uses ``models.Manager()`` semantics on tenant-owned models inside
      data migrations. Migrations that need tenant scoping MUST filter
      explicitly. This prevents accidental ``RelatedManager``-style
      auto-filtering inside historical model proxies.
    * No auto-filtering: the manager does not inject any
      ``organization_id`` filter on its own. Service-layer reads MUST
      call ``for_org`` or ``for_membership`` explicitly.
    """

    use_in_migrations: bool = False

    # Manager.from_queryset(TenantQuerySet) generates these methods at
    # class creation; the type stubs don't always pick up that
    # generation. Re-declaring them here gives mypy/IDE a concrete
    # signature for the proxies and documents the surface.

    def for_org(self, organization_id: UUID) -> TenantQuerySet:  # pragma: no cover
        return self.get_queryset().for_org(organization_id)

    def for_membership(self, membership: Any) -> TenantQuerySet:  # pragma: no cover
        return self.get_queryset().for_membership(membership)
