"""Dev-only Django admin registration for the User model.

This is mounted ONLY at ``/django-admin/`` and ONLY in DEBUG (see
``config/urls.py``). It is for raw model inspection during development
(H.7.2). The production admin surface is the custom platform admin
(H.7.1).
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.platform.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Minimal raw-inspection admin. Not a product surface."""

    ordering = ("email",)
    list_display = ("email", "is_active", "is_staff", "is_superuser", "is_system")
    list_filter = ("is_active", "is_staff", "is_superuser", "is_system")
    search_fields = ("email",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_login",
        "password_changed_at",
        "last_login_at",
    )

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Flags",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_system",
                    "external_login_only",
                    "preferred_auth_method",
                )
            },
        ),
        (
            "MFA / security",
            {
                "fields": (
                    "totp_enrolled_at",
                    "failed_login_count",
                    "locked_until",
                    "password_changed_at",
                    "last_password_breach_check_at",
                ),
                "description": (
                    "Sensitive secrets (TOTP secret, backup-code hash) are intentionally "
                    "not surfaced here. Manage via service-layer flows."
                ),
            },
        ),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        (
            "Timestamps",
            {"fields": ("last_login", "last_login_at", "created_at", "updated_at")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )
