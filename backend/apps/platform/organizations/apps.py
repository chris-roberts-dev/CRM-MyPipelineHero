from __future__ import annotations

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    name = "apps.platform.organizations"
    label = "platform_organizations"
    verbose_name = "Platform · Organizations"
    default_auto_field = "django.db.models.BigAutoField"
