"""Initial migration for platform_organizations.

Creates Organization, Membership, TenantExportRequest, TenantDeletionRequest.
Depends on platform_accounts.0001 (custom User model).
"""

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.platform.organizations.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("platform_accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.organizations.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("slug", models.CharField(max_length=63, unique=True)),
                ("name", models.CharField(max_length=200)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("SUSPENDED", "Suspended"),
                            ("OFFBOARDING", "Offboarding"),
                            ("DELETED", "Deleted"),
                        ],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                (
                    "primary_contact_name",
                    models.CharField(blank=True, default="", max_length=200),
                ),
                ("primary_contact_email", models.EmailField(max_length=254)),
                (
                    "primary_contact_phone",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "timezone",
                    models.CharField(default="America/Chicago", max_length=64),
                ),
                ("base_currency_code", models.CharField(default="USD", max_length=3)),
                (
                    "default_tax_jurisdiction_id",
                    models.UUIDField(blank=True, null=True),
                ),
                ("invoicing_policy_id", models.UUIDField(blank=True, null=True)),
                ("numbering_config", models.JSONField(blank=True, default=dict)),
                (
                    "accounting_adapter_code",
                    models.CharField(default="noop", max_length=64),
                ),
                (
                    "accounting_adapter_config",
                    models.JSONField(blank=True, default=dict),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "organization",
                "verbose_name_plural": "organizations",
            },
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(fields=["status"], name="platform_or_status_idx"),
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.organizations.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("INVITED", "Invited"),
                            ("ACTIVE", "Active"),
                            ("SUSPENDED", "Suspended"),
                            ("INACTIVE", "Inactive"),
                            ("EXPIRED", "Expired"),
                        ],
                        default="INVITED",
                        max_length=16,
                    ),
                ),
                ("invited_at", models.DateTimeField(blank=True, null=True)),
                ("invitation_expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "invitation_token_hash",
                    models.CharField(blank=True, max_length=128, null=True),
                ),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("first_name", models.CharField(blank=True, default="", max_length=80)),
                ("last_name", models.CharField(blank=True, default="", max_length=80)),
                ("phone", models.CharField(blank=True, max_length=64, null=True)),
                ("is_default_for_user", models.BooleanField(default=False)),
                ("suspended_reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to="platform_organizations.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "membership",
                "verbose_name_plural": "memberships",
            },
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                fields=("user", "organization"),
                name="platform_organizations_membership_user_org_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_default_for_user=True),
                fields=("user",),
                name="platform_organizations_membership_one_default_per_user",
            ),
        ),
        migrations.AddIndex(
            model_name="membership",
            index=models.Index(
                fields=["user", "organization"],
                name="platform_or_user_id_org_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="membership",
            index=models.Index(
                fields=["organization", "status"],
                name="platform_or_org_id_status_idx",
            ),
        ),
        migrations.CreateModel(
            name="TenantExportRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.organizations.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                (
                    "requested_scope",
                    models.CharField(
                        choices=[
                            ("FULL", "Full"),
                            ("COMMERCIAL_ONLY", "Commercial only"),
                            ("AUDIT_ONLY", "Audit only"),
                        ],
                        default="FULL",
                        max_length=24,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("QUEUED", "Queued"),
                            ("ASSEMBLING", "Assembling"),
                            ("READY", "Ready"),
                            ("DOWNLOADED", "Downloaded"),
                            ("EXPIRED", "Expired"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="QUEUED",
                        max_length=16,
                    ),
                ),
                ("output_attachment_id", models.UUIDField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True, default="")),
                ("bytes_size", models.BigIntegerField(blank=True, null=True)),
                ("row_count", models.BigIntegerField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "cancelled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="export_requests",
                        to="platform_organizations.organization",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "tenant export request",
                "verbose_name_plural": "tenant export requests",
            },
        ),
        migrations.AddIndex(
            model_name="tenantexportrequest",
            index=models.Index(
                fields=["organization", "status"],
                name="platform_or_org_id_status_xpt_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="tenantexportrequest",
            index=models.Index(
                fields=["status", "expires_at"],
                name="platform_or_status_expires_idx",
            ),
        ),
        migrations.CreateModel(
            name="TenantDeletionRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.organizations.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("GRACE_PERIOD", "Grace period"),
                            ("EXECUTING", "Executing"),
                            ("EXECUTED", "Executed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        default="GRACE_PERIOD",
                        max_length=16,
                    ),
                ),
                ("grace_period_ends_at", models.DateTimeField()),
                ("confirmation_phrase_provided", models.CharField(max_length=63)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_reason", models.TextField(blank=True, default="")),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                ("rows_deleted_per_table", models.JSONField(blank=True, null=True)),
                (
                    "cancelled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "executed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deletion_requests",
                        to="platform_organizations.organization",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "tenant deletion request",
                "verbose_name_plural": "tenant deletion requests",
            },
        ),
        migrations.AddIndex(
            model_name="tenantdeletionrequest",
            index=models.Index(
                fields=["organization", "status"],
                name="platform_or_org_status_del_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="tenantdeletionrequest",
            index=models.Index(
                fields=["status", "grace_period_ends_at"],
                name="platform_or_status_grace_idx",
            ),
        ),
    ]
