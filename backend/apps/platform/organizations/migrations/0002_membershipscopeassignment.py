"""MembershipScopeAssignment table + CHECK constraints (B.2.4)."""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platform_organizations", "0001_initial"),
        ("operations_locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MembershipScopeAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("REGION", "Region"),
                            ("MARKET", "Market"),
                            ("LOCATION", "Location"),
                        ],
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "membership",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="scope_assignments",
                        to="platform_organizations.membership",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to="operations_locations.region",
                    ),
                ),
                (
                    "market",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to="operations_locations.market",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to="operations_locations.location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Membership scope assignment",
                "verbose_name_plural": "Membership scope assignments",
            },
        ),
        migrations.AddConstraint(
            model_name="membershipscopeassignment",
            constraint=models.CheckConstraint(
                name="scope_assignment_exactly_one_target",
                condition=(
                    models.Q(
                        region__isnull=True,
                        market__isnull=True,
                        location__isnull=False,
                    )
                    | models.Q(
                        region__isnull=True,
                        market__isnull=False,
                        location__isnull=True,
                    )
                    | models.Q(
                        region__isnull=False,
                        market__isnull=True,
                        location__isnull=True,
                    )
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name="membershipscopeassignment",
            constraint=models.CheckConstraint(
                name="scope_type_matches_target_fk",
                condition=(
                    models.Q(scope_type="REGION", region__isnull=False)
                    | models.Q(scope_type="MARKET", market__isnull=False)
                    | models.Q(scope_type="LOCATION", location__isnull=False)
                ),
            ),
        ),
        migrations.RenameIndex(
            model_name="tenantexportrequest",
            new_name="platform_or_export_org_st_idx",
            old_name="platform_or_org_id_status_xpt_idx",
        ),
    ]
