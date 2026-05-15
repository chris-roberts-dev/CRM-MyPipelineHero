"""Dev-only Django admin registrations for RML models.

Mounted at ``/django-admin/`` and only visible when DEBUG=True. The
production platform console (custom admin at ``/platform/``) gets the
proper RML editing surface in a later milestone.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin

from apps.operations.locations.models import Location, Market, Region

if settings.DEBUG:

    @admin.register(Region)
    class RegionAdmin(admin.ModelAdmin):
        list_display = ("code", "name", "organization", "is_active", "created_at")
        list_filter = ("organization", "is_active")
        search_fields = ("code", "name")
        ordering = ("organization", "code")
        readonly_fields = ("id", "created_at", "updated_at")

    @admin.register(Market)
    class MarketAdmin(admin.ModelAdmin):
        list_display = (
            "code",
            "name",
            "region",
            "organization",
            "is_active",
            "created_at",
        )
        list_filter = ("organization", "region", "is_active")
        search_fields = ("code", "name")
        ordering = ("organization", "code")
        readonly_fields = ("id", "created_at", "updated_at")

    @admin.register(Location)
    class LocationAdmin(admin.ModelAdmin):
        list_display = (
            "code",
            "name",
            "market",
            "organization",
            "city",
            "region_admin",
            "is_active",
            "created_at",
        )
        list_filter = ("organization", "market", "is_active", "country", "region_admin")
        search_fields = ("code", "name", "address_line1", "city", "postal_code")
        ordering = ("organization", "code")
        readonly_fields = ("id", "created_at", "updated_at")
        fieldsets = (
            (
                None,
                {
                    "fields": (
                        "id",
                        "organization",
                        "market",
                        "code",
                        "name",
                        "is_active",
                    )
                },
            ),
            (
                "Address",
                {
                    "fields": (
                        "address_line1",
                        "address_line2",
                        "city",
                        "region_admin",
                        "postal_code",
                        "country",
                    ),
                },
            ),
            (
                "Tax",
                {"fields": ("tax_jurisdiction_id",)},
            ),
            (
                "Audit",
                {"fields": ("created_at", "updated_at", "created_by", "updated_by")},
            ),
        )
