"""Migration #1 for platform_accounts.

This migration creates the canonical ``User`` model. It MUST exist as
``0001_initial`` per the technical guide (I.6.7). The custom user model
baseline check (``scripts/check_user_model_baseline.py``) verifies this.

Subsequent platform-level migrations (organizations, rbac) depend on
this one (I.6.8).
"""

from __future__ import annotations

import uuid

import django.contrib.auth.models
import django.db.models.deletion
import django.db.models.functions
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import apps.platform.accounts.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=apps.platform.accounts.models._new_user_uuid,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Designates that this user has all permissions without "
                            "explicitly assigning them."
                        ),
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        max_length=254, unique=True, verbose_name="email address"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="User may access the platform console (B.3.4).",
                    ),
                ),
                (
                    "is_system",
                    models.BooleanField(
                        default=False,
                        help_text="Exactly one System User exists per environment (B.3.10).",
                    ),
                ),
                ("totp_secret", models.TextField(blank=True, null=True)),
                ("totp_enrolled_at", models.DateTimeField(blank=True, null=True)),
                ("backup_codes_hash", models.TextField(blank=True, null=True)),
                ("password_changed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "last_password_breach_check_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                ("failed_login_count", models.PositiveIntegerField(default=0)),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                (
                    "preferred_auth_method",
                    models.CharField(
                        choices=[
                            ("PASSWORD", "Password"),
                            ("OIDC", "OAuth/OIDC"),
                            ("EITHER", "Either"),
                        ],
                        default="EITHER",
                        max_length=16,
                    ),
                ),
                ("external_login_only", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "The groups this user belongs to. A user will get all "
                            "permissions granted to each of their groups."
                        ),
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
            managers=[
                ("objects", apps.platform.accounts.models.UserManager()),
            ],
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("email", django.db.models.functions.Lower("email"))
                ),
                name="platform_accounts_user_email_lowercase",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("is_system", False),
                    models.Q(
                        ("is_active", True),
                        ("is_staff", False),
                        ("is_superuser", False),
                    ),
                    _connector="OR",
                ),
                name="platform_accounts_user_system_user_invariant",
            ),
        ),
    ]
