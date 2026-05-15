"""Region / Market / Location models (B.2.2).

All three inherit from :class:`apps.common.tenancy.models.TenantOwnedModel`,
which gives them:

* an ``organization`` FK with ``on_delete=PROTECT``,
* ``created_at`` / ``updated_at`` / ``created_by`` / ``updated_by`` audit columns,
* ``is_tenant_owned = True`` (so the B.1.7 guardrail picks them up),
* a default manager that is a :class:`TenantManager` subclass.

Hierarchy invariants (B.2.1):

* A Market belongs to exactly one Region.
* A Location belongs to exactly one Market.
* Cross-organization references are prohibited. This is enforced at
  the service layer via :func:`apps.common.tenancy.utils.ensure_same_org`.
  No cross-row DB CHECK constraint is used (B.1.6 forbids that pattern
  in v1).
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.common.tenancy.managers import TenantManager, TenantQuerySet
from apps.common.tenancy.models import TenantOwnedModel

# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------


class Region(TenantOwnedModel):
    """Top-level operating-scope grouping within an Organization (B.2.2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "operations_locations"
        verbose_name = "Region"
        verbose_name_plural = "Regions"
        unique_together = [("organization", "code")]
        ordering = ["organization_id", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------


class Market(TenantOwnedModel):
    """Mid-level operating-scope grouping, child of a Region (B.2.2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="markets",
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "operations_locations"
        verbose_name = "Market"
        verbose_name_plural = "Markets"
        unique_together = [("organization", "code")]
        ordering = ["organization_id", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Location — with per-model QuerySet (B.2.5 pattern)
# ---------------------------------------------------------------------------


class LocationQuerySet(TenantQuerySet):
    """Per-model QuerySet for Location.

    Location is the *leaf* of the operating-scope hierarchy: every
    permitted Location id IS itself the row this queryset returns. So
    rather than filtering ``location_id__in=...`` (the pattern in
    B.2.5's SalesOrder example), we filter ``id__in=...``.

    The membership-no-scope-assignments rules from B.2.5 still apply:

    * No assignments + non-scoped role  → org-wide access (return self).
    * No assignments + scoped role      → zero access (return self.none()).
    * Has assignments                   → filter to the permitted set.
    """

    def intersect_with_operating_scope(self, membership) -> LocationQuerySet:  # type: ignore[override]
        # Avoid the import cycle: resolve_location_ids_for_scopes lives
        # in apps.common.tenancy.utils which itself depends on this
        # package indirectly via models registry walks. Import locally.
        from apps.common.tenancy.utils import resolve_location_ids_for_scopes

        scopes = list(membership.scope_assignments.all())
        if not scopes:
            if membership.role_assignments.filter(role__is_scoped_role=True).exists():
                return self.none()
            return self
        permitted = resolve_location_ids_for_scopes(scopes)
        return self.filter(id__in=permitted)


class LocationManager(TenantManager.from_queryset(LocationQuerySet)):  # type: ignore[misc]
    """Default manager for Location.

    Reuses TenantManager's invariants (use_in_migrations=False) and
    layers on the LocationQuerySet method surface.
    """

    use_in_migrations: bool = False


class Location(TenantOwnedModel):
    """Leaf node in the operating-scope hierarchy (B.2.2).

    The address fields are denormalized for fast display and for
    pricing/tax inputs (B.2.7). The ``region_admin`` field holds the
    administrative region (state/province) — note this is unrelated to
    the operating-scope ``region`` FK on Market.

    ``tax_jurisdiction_id`` is a plain UUID column awaiting the
    TaxJurisdiction model that lands in M3 (J.5). It will be converted
    to a real FK at that time. Same pattern as
    ``Organization.default_tax_jurisdiction_id`` from M0 D2.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(
        Market,
        on_delete=models.PROTECT,
        related_name="locations",
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)

    # Address fields (B.2.2)
    address_line1 = models.CharField(max_length=256, blank=True, default="")
    address_line2 = models.CharField(max_length=256, blank=True, default="")
    city = models.CharField(max_length=128, blank=True, default="")
    region_admin = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text=(
            "Administrative region (state/province). Unrelated to the "
            "operating-scope Region attached via market.region."
        ),
    )
    postal_code = models.CharField(max_length=32, blank=True, default="")
    country = models.CharField(max_length=64, blank=True, default="")

    tax_jurisdiction_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "Plain UUID column awaiting M3 TaxJurisdiction model. "
            "Converted to a real FK at that milestone."
        ),
    )

    is_active = models.BooleanField(default=True)

    objects = LocationManager()  # type: ignore[assignment]

    class Meta:
        app_label = "operations_locations"
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        unique_together = [("organization", "code")]
        ordering = ["organization_id", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
