from __future__ import annotations

from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.platform.audit"
    label = "platform_audit"
    verbose_name = "Platform · Audit"
    default_auto_field = "django.db.models.BigAutoField"
