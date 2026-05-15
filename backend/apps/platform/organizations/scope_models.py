"""MembershipScopeAssignment (B.2.4).

Lives in ``apps.platform.organizations`` because it joins Membership
(an organizations-app model) with RML rows. The cross-app dependency
direction is: ``platform_organizations`` → ``operations_locations``.

CHECK constraint enforces "exactly one of (region_id, market_id,
location_id) is non-null" per the B.2.4 spec.

NOT a TenantOwnedModel subclass:

* MembershipScopeAssignment isn't a tenant-owned record in the
  same sense as a domain entity. It's a JOIN row owned by a
  Membership. The platform console may legitimately query these
  across tenants.
* The organization is reachable transitively via
  ``self.membership.organization_id``. Adding a redundant org column
  would invite drift.
"""

from __future__ import annotations

import uuid

from django.db import models


class MembershipScopeAssignment(models.Model):
    """Per-Membership scope grant at REGION, MARKET, or LOCATION granularity."""

    SCOPE_TYPE_REGION = "REGION"
    SCOPE_TYPE_MARKET = "MARKET"
    SCOPE_TYPE_LOCATION = "LOCATION"
    SCOPE_TYPE_CHOICES = [
        (SCOPE_TYPE_REGION, "Region"),
        (SCOPE_TYPE_MARKET, "Market"),
        (SCOPE_TYPE_LOCATION, "Location"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(
        "platform_organizations.Membership",
        on_delete=models.CASCADE,
        related_name="scope_assignments",
    )
    scope_type = models.CharField(max_length=16, choices=SCOPE_TYPE_CHOICES)

    region = models.ForeignKey(
        "operations_locations.Region",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    market = models.ForeignKey(
        "operations_locations.Market",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    location = models.ForeignKey(
        "operations_locations.Location",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "platform_organizations"
        verbose_name = "Membership scope assignment"
        verbose_name_plural = "Membership scope assignments"
        constraints = [
            # Per B.2.4: "exactly one of (region_id, market_id, location_id)
            # is non-null". Encoded as "exactly two are null".
            models.CheckConstraint(
                name="scope_assignment_exactly_one_target",
                condition=(
                    models.Q(
                        region__isnull=True, market__isnull=True, location__isnull=False
                    )
                    | models.Q(
                        region__isnull=True, market__isnull=False, location__isnull=True
                    )
                    | models.Q(
                        region__isnull=False, market__isnull=True, location__isnull=True
                    )
                ),
            ),
            # The scope_type must match which FK is populated.
            models.CheckConstraint(
                name="scope_type_matches_target_fk",
                condition=(
                    models.Q(scope_type="REGION", region__isnull=False)
                    | models.Q(scope_type="MARKET", market__isnull=False)
                    | models.Q(scope_type="LOCATION", location__isnull=False)
                ),
            ),
        ]

    def __str__(self) -> str:
        target = self.region or self.market or self.location
        return f"{self.scope_type}: {target}"
