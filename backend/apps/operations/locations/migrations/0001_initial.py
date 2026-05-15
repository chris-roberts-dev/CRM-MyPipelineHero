"""Initial RML schema (B.2.2)."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("platform_organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -----------------------------------------------------------------
        # Region
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="Region",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=128)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to="platform_organizations.organization",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Region",
                "verbose_name_plural": "Regions",
                "ordering": ["organization_id", "code"],
                "unique_together": {("organization", "code")},
            },
        ),
        # -----------------------------------------------------------------
        # Market
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="Market",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=128)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to="platform_organizations.organization",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="markets",
                        to="operations_locations.region",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Market",
                "verbose_name_plural": "Markets",
                "ordering": ["organization_id", "code"],
                "unique_together": {("organization", "code")},
            },
        ),
        # -----------------------------------------------------------------
        # Location
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="Location",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=128)),
                (
                    "address_line1",
                    models.CharField(blank=True, default="", max_length=256),
                ),
                (
                    "address_line2",
                    models.CharField(blank=True, default="", max_length=256),
                ),
                ("city", models.CharField(blank=True, default="", max_length=128)),
                (
                    "region_admin",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text=(
                            "Administrative region (state/province). Unrelated to the "
                            "operating-scope Region attached via market.region."
                        ),
                        max_length=128,
                    ),
                ),
                (
                    "postal_code",
                    models.CharField(blank=True, default="", max_length=32),
                ),
                ("country", models.CharField(blank=True, default="", max_length=64)),
                (
                    "tax_jurisdiction_id",
                    models.UUIDField(
                        blank=True,
                        help_text=(
                            "Plain UUID column awaiting M3 TaxJurisdiction model. "
                            "Converted to a real FK at that milestone."
                        ),
                        null=True,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to="platform_organizations.organization",
                    ),
                ),
                (
                    "market",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        related_name="locations",
                        to="operations_locations.market",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Location",
                "verbose_name_plural": "Locations",
                "ordering": ["organization_id", "code"],
                "unique_together": {("organization", "code")},
            },
        ),
    ]
