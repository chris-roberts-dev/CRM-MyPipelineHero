from __future__ import annotations

from django.apps import AppConfig


class RbacConfig(AppConfig):
    name = "apps.platform.rbac"
    label = "platform_rbac"
    verbose_name = "Platform · RBAC"
    default_auto_field = "django.db.models.BigAutoField"
