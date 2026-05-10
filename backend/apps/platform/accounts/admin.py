"""Dev-only Django admin registrations.

This module is loaded ONLY when ``/django-admin/`` is mounted (DEBUG=True
per config/urls.py). It is for raw model inspection during development
(H.7.2). The production admin surface is the custom platform admin
(H.7.1).

Each registration uses ``ModelAdmin`` with conservative settings —
readonly timestamps, search by stable fields, list display tuned for
quick eyeballing. No bulk-edit, no save-as-new, no inline form magic.
None of these surfaces are product workflows.
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.platform.accounts.models import User
from apps.platform.organizations.models import (
    Membership,
    Organization,
    TenantDeletionRequest,
    TenantExportRequest,
)
from apps.platform.rbac.models import (
    Capability,
    MembershipCapabilityGrant,
    MembershipRole,
    Role,
    RoleCapability,
)

# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "status", "base_currency_code", "created_at")
    list_filter = ("status", "base_currency_code")
    search_fields = ("slug", "name", "primary_contact_email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("slug",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "status",
        "is_default_for_user",
        "accepted_at",
    )
    list_filter = ("status", "is_default_for_user")
    search_fields = ("user__email", "organization__slug", "first_name", "last_name")
    readonly_fields = ("id", "created_at", "updated_at", "accepted_at")
    autocomplete_fields = ("user", "organization", "invited_by")
    ordering = ("-created_at",)


@admin.register(TenantExportRequest)
class TenantExportRequestAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "requested_scope",
        "status",
        "requested_at",
        "expires_at",
    )
    list_filter = ("status", "requested_scope")
    search_fields = ("organization__slug",)
    readonly_fields = ("id", "requested_at")
    autocomplete_fields = ("organization", "requested_by", "cancelled_by")
    ordering = ("-requested_at",)


@admin.register(TenantDeletionRequest)
class TenantDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ("organization", "status", "requested_at", "grace_period_ends_at")
    list_filter = ("status",)
    search_fields = ("organization__slug",)
    readonly_fields = ("id", "requested_at")
    autocomplete_fields = (
        "organization",
        "requested_by",
        "cancelled_by",
        "executed_by",
    )
    ordering = ("-requested_at",)


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "name", "is_deprecated")
    list_filter = ("category", "is_deprecated")
    search_fields = ("code", "name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("category", "code")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "organization",
        "is_default",
        "is_scoped_role",
        "is_locked",
    )
    list_filter = ("is_default", "is_scoped_role", "is_locked")
    search_fields = ("code", "name", "organization__slug")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("organization",)
    ordering = ("organization", "code")


@admin.register(RoleCapability)
class RoleCapabilityAdmin(admin.ModelAdmin):
    list_display = ("role", "capability")
    search_fields = ("role__code", "capability__code")
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("role", "capability")


@admin.register(MembershipRole)
class MembershipRoleAdmin(admin.ModelAdmin):
    list_display = ("membership", "role", "assigned_at")
    search_fields = ("membership__user__email", "role__code")
    readonly_fields = ("id", "assigned_at")
    autocomplete_fields = ("membership", "role", "assigned_by")


@admin.register(MembershipCapabilityGrant)
class MembershipCapabilityGrantAdmin(admin.ModelAdmin):
    list_display = ("membership", "capability", "grant_type", "granted_at")
    list_filter = ("grant_type",)
    search_fields = ("membership__user__email", "capability__code")
    readonly_fields = ("id", "granted_at")
    autocomplete_fields = ("membership", "capability", "granted_by")
