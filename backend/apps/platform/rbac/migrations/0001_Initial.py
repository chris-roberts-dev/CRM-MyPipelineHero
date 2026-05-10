"""Initial migration for platform_rbac.

Creates Capability, Role, RoleCapability, MembershipRole, and
MembershipCapabilityGrant. Depends on platform_organizations.0001
(Organization, Membership) and platform_accounts.0001 (User).
"""

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.platform.rbac.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("platform_accounts", "0001_Initial"),
        ("platform_organizations", "0001_Initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Capability",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.rbac.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("code", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True, default="")),
                ("category", models.CharField(max_length=64)),
                ("is_deprecated", models.BooleanField(default=False)),
                (
                    "deprecated_in_version",
                    models.CharField(blank=True, max_length=32, null=True),
                ),
                (
                    "deprecated_replacement_code",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "capability",
                "verbose_name_plural": "capabilities",
            },
        ),
        migrations.AddIndex(
            model_name="capability",
            index=models.Index(fields=["category"], name="platform_rb_categ_idx"),
        ),
        migrations.AddIndex(
            model_name="capability",
            index=models.Index(fields=["is_deprecated"], name="platform_rb_dep_idx"),
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.rbac.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("code", models.CharField(max_length=64)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True, default="")),
                ("is_default", models.BooleanField(default=False)),
                (
                    "is_scoped_role",
                    models.BooleanField(
                        default=False,
                        help_text="If True, membership scope assignments restrict access (B.2.5).",
                    ),
                ),
                (
                    "is_locked",
                    models.BooleanField(
                        default=False,
                        help_text="If True, capabilities cannot be edited via tenant admin.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        help_text="NULL for default templates; concrete org for tenant-scoped roles.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="roles",
                        to="platform_organizations.organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "role",
                "verbose_name_plural": "roles",
            },
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(
                condition=models.Q(("organization__isnull", False)),
                fields=("organization", "code"),
                name="platform_rbac_role_org_code_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(
                condition=models.Q(("organization__isnull", True)),
                fields=("code",),
                name="platform_rbac_role_template_code_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(
                fields=["organization", "is_default"],
                name="platform_rb_org_def_idx",
            ),
        ),
        migrations.CreateModel(
            name="RoleCapability",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.rbac.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "capability",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="role_capabilities",
                        to="platform_rbac.capability",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_capabilities",
                        to="platform_rbac.role",
                    ),
                ),
            ],
            options={
                "verbose_name": "role capability",
                "verbose_name_plural": "role capabilities",
            },
        ),
        migrations.AddConstraint(
            model_name="rolecapability",
            constraint=models.UniqueConstraint(
                fields=("role", "capability"),
                name="platform_rbac_rolecap_unique",
            ),
        ),
        migrations.CreateModel(
            name="MembershipRole",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.rbac.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to="platform_organizations.membership",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="member_assignments",
                        to="platform_rbac.role",
                    ),
                ),
            ],
            options={
                "verbose_name": "membership role",
                "verbose_name_plural": "membership roles",
            },
        ),
        migrations.AddConstraint(
            model_name="membershiprole",
            constraint=models.UniqueConstraint(
                fields=("membership", "role"),
                name="platform_rbac_membershiprole_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="membershiprole",
            index=models.Index(fields=["membership"], name="platform_rb_memb_idx"),
        ),
        migrations.CreateModel(
            name="MembershipCapabilityGrant",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.rbac.models._new_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "grant_type",
                    models.CharField(
                        choices=[("GRANT", "Grant"), ("DENY", "Deny")],
                        max_length=8,
                    ),
                ),
                ("reason", models.TextField()),
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "capability",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="membership_grants",
                        to="platform_rbac.capability",
                    ),
                ),
                (
                    "granted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="capability_grants",
                        to="platform_organizations.membership",
                    ),
                ),
            ],
            options={
                "verbose_name": "membership capability grant",
                "verbose_name_plural": "membership capability grants",
            },
        ),
        migrations.AddConstraint(
            model_name="membershipcapabilitygrant",
            constraint=models.UniqueConstraint(
                fields=("membership", "capability"),
                name="platform_rbac_membershipcapgrant_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="membershipcapabilitygrant",
            index=models.Index(
                fields=["membership"], name="platform_rb_memb_grant_idx"
            ),
        ),
    ]
